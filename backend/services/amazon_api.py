import json
import time
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from loguru import logger

from models.database import FeedType, AmazonCredentials

class AWSSignatureV4:
    """
    Implementacja AWS Signature Version 4 dla Amazon SP-API
    """

    def __init__(self, access_key: str, secret_key: str, region: str = 'us-east-1'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = 'execute-api'

    def sign_request(self, method: str, url: str, headers: Dict[str, str], payload: str = '') -> Dict[str, str]:
        """
        Podpisanie żądania za pomocą AWS SigV4
        """
        # Parse URL
        parsed_url = urllib.parse.urlparse(url)
        canonical_uri = parsed_url.path or '/'
        canonical_querystring = parsed_url.query or ''

        # Timestamp
        t = datetime.now(timezone.utc)
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')

        # Add required headers
        headers = headers.copy()
        headers['host'] = parsed_url.netloc
        headers['x-amz-date'] = amz_date

        # Create canonical headers
        canonical_headers = ''
        signed_headers = ''
        header_names = sorted(headers.keys())
        for name in header_names:
            canonical_headers += f"{name.lower()}:{headers[name].strip()}\n"
            signed_headers += f"{name.lower()};"
        signed_headers = signed_headers[:-1]  # Remove trailing semicolon

        # Create payload hash
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        # Create canonical request
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        # Calculate signature
        signing_key = self._get_signature_key(self.secret_key, date_stamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        # Add authorization header
        authorization_header = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        headers['Authorization'] = authorization_header

        return headers

    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        """
        Generowanie klucza podpisu
        """
        k_date = hmac.new(f"AWS4{key}".encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region_name.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service_name.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, "aws4_request".encode('utf-8'), hashlib.sha256).digest()
        return k_signing

class AmazonSPAPIService:
    """
    Serwis do komunikacji z Amazon SP-API
    """

    def __init__(self, credentials: AmazonCredentials):
        self.credentials = credentials
        self.base_url = "https://sellingpartnerapi-na.amazon.com" if not credentials.is_sandbox else "https://sandbox.sellingpartnerapi-na.amazon.com"
        self.aws_signer = AWSSignatureV4(
            credentials.aws_access_key,
            credentials.aws_secret_key,
            credentials.aws_region
        )
        self.access_token = None
        self.token_expires_at = None

    async def get_access_token(self) -> str:
        """
        Pobieranie access token dla SP-API
        """
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token

        token_url = "https://api.amazon.com/auth/o2/token"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.credentials.refresh_token,
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to get access token: {response.text}")
                raise Exception(f"Failed to get access token: {response.status_code}")

            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + datetime.timedelta(seconds=expires_in - 60)  # 60s buffer

            logger.info("Successfully obtained access token")
            return self.access_token

    async def make_signed_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Wykonanie podpisanego żądania do SP-API
        """
        access_token = await self.get_access_token()
        url = f"{self.base_url}{endpoint}"

        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json"
        }

        payload = json.dumps(data) if data else ""

        # Podpisanie żądania
        signed_headers = self.aws_signer.sign_request(method, url, headers, payload)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=signed_headers,
                content=payload
            )

            if response.status_code == 429:  # Rate limiting
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                return await self.make_signed_request(method, endpoint, data, params)

            if response.status_code not in [200, 201, 202]:
                logger.error(f"SP-API request failed: {response.status_code} - {response.text}")
                response.raise_for_status()

            return response.json()

    async def create_feed_document(self, content_type: str = "application/json") -> Dict[str, Any]:
        """
        Utworzenie feed document dla uploadu danych
        """
        endpoint = "/feeds/2021-06-30/documents"
        data = {
            "contentType": content_type
        }

        response = await self.make_signed_request("POST", endpoint, data)
        return response

    async def upload_feed_document(self, upload_url: str, content: str, content_type: str = "application/json") -> None:
        """
        Upload danych do feed document
        """
        headers = {
            "Content-Type": content_type
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(
                upload_url,
                content=content,
                headers=headers
            )

            if response.status_code not in [200, 204]:
                logger.error(f"Failed to upload feed document: {response.status_code} - {response.text}")
                response.raise_for_status()

    async def create_feed(self, feed_type: str, input_feed_document_id: str) -> Dict[str, Any]:
        """
        Utworzenie feeda w Amazon SP-API
        """
        endpoint = "/feeds/2021-06-30/feeds"

        data = {
            "feedType": feed_type,
            "marketplaceIds": [self.credentials.marketplace_id],
            "inputFeedDocumentId": input_feed_document_id
        }

        response = await self.make_signed_request("POST", endpoint, data)
        return response

    async def get_feed_status(self, feed_id: str) -> Dict[str, Any]:
        """
        Sprawdzenie statusu feeda
        """
        endpoint = f"/feeds/2021-06-30/feeds/{feed_id}"
        response = await self.make_signed_request("GET", endpoint)
        return response

    async def get_feed_result_document(self, result_feed_document_id: str) -> Dict[str, Any]:
        """
        Pobranie dokumentu z wynikami feeda
        """
        endpoint = f"/feeds/2021-06-30/documents/{result_feed_document_id}"
        response = await self.make_signed_request("GET", endpoint)
        return response

    async def download_feed_result(self, download_url: str) -> str:
        """
        Pobranie zawartości dokumentu z wynikami
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(download_url)
            response.raise_for_status()
            return response.text

    async def submit_inventory_feed(self, inventory_data: List[Dict[str, Any]]) -> str:
        """
        Wysłanie feeda inventory do Amazon SP-API
        """
        # Mapowanie danych do formatu JSON_LISTINGS_FEED
        feed_data = {
            "header": {
                "sellerId": self.credentials.seller_id,
                "version": "2021-06-30",
                "issueLocale": "en_US"
            },
            "messages": []
        }

        for item in inventory_data:
            message = {
                "messageId": item.get("sku"),
                "sku": item.get("sku"),
                "operationType": "UPDATE",
                "productType": "GENERIC",
                "attributes": {
                    "fulfillment_availability": [
                        {
                            "fulfillment_channel_code": "DEFAULT",
                            "quantity": item.get("quantity", 0)
                        }
                    ]
                }
            }
            feed_data["messages"].append(message)

        # Konwersja do JSON
        json_content = json.dumps(feed_data, indent=2)

        # Utworzenie feed document
        doc_response = await self.create_feed_document()
        upload_url = doc_response["url"]
        document_id = doc_response["feedDocumentId"]

        # Upload danych
        await self.upload_feed_document(upload_url, json_content)

        # Utworzenie feeda
        feed_response = await self.create_feed("JSON_LISTINGS_FEED", document_id)

        logger.info(f"Successfully submitted inventory feed: {feed_response['feedId']}")
        return feed_response["feedId"]

    async def submit_pricing_feed(self, pricing_data: List[Dict[str, Any]]) -> str:
        """
        Wysłanie feeda pricing do Amazon SP-API
        """
        feed_data = {
            "header": {
                "sellerId": self.credentials.seller_id,
                "version": "2021-06-30",
                "issueLocale": "en_US"
            },
            "messages": []
        }

        for item in pricing_data:
            message = {
                "messageId": item.get("sku"),
                "sku": item.get("sku"),
                "operationType": "UPDATE",
                "productType": "GENERIC",
                "attributes": {
                    "purchasable_offer": [
                        {
                            "currency": item.get("currency", "USD"),
                            "our_price": [
                                {
                                    "schedule": [
                                        {
                                            "value_with_tax": item.get("price", 0)
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
            feed_data["messages"].append(message)

        json_content = json.dumps(feed_data, indent=2)

        # Proces uploadu podobny jak w inventory
        doc_response = await self.create_feed_document()
        await self.upload_feed_document(doc_response["url"], json_content)
        feed_response = await self.create_feed("JSON_LISTINGS_FEED", doc_response["feedDocumentId"])

        logger.info(f"Successfully submitted pricing feed: {feed_response['feedId']}")
        return feed_response["feedId"]

    async def submit_listings_feed(self, listings_data: List[Dict[str, Any]]) -> str:
        """
        Wysłanie feeda listings (produkty) do Amazon SP-API
        """
        feed_data = {
            "header": {
                "sellerId": self.credentials.seller_id,
                "version": "2021-06-30",
                "issueLocale": "en_US"
            },
            "messages": []
        }

        for item in listings_data:
            message = {
                "messageId": item.get("sku"),
                "sku": item.get("sku"),
                "operationType": "UPDATE",
                "productType": "GENERIC",
                "attributes": {
                    "item_name": [
                        {
                            "value": item.get("title", ""),
                            "language_tag": "en_US"
                        }
                    ],
                    "description": [
                        {
                            "value": item.get("description", ""),
                            "language_tag": "en_US"
                        }
                    ],
                    "brand": [
                        {
                            "value": item.get("brand", "")
                        }
                    ],
                    "purchasable_offer": [
                        {
                            "currency": "USD",
                            "our_price": [
                                {
                                    "schedule": [
                                        {
                                            "value_with_tax": item.get("price", 0)
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
            feed_data["messages"].append(message)

        json_content = json.dumps(feed_data, indent=2)

        doc_response = await self.create_feed_document()
        await self.upload_feed_document(doc_response["url"], json_content)
        feed_response = await self.create_feed("JSON_LISTINGS_FEED", doc_response["feedDocumentId"])

        logger.info(f"Successfully submitted listings feed: {feed_response['feedId']}")
        return feed_response["feedId"]

    def get_feed_type_mapping(self, feed_type: FeedType) -> str:
        """
        Mapowanie wewnętrznych typów feedów na typy Amazon SP-API
        """
        mapping = {
            FeedType.INVENTORY: "JSON_LISTINGS_FEED",
            FeedType.PRICING: "JSON_LISTINGS_FEED",
            FeedType.LISTINGS: "JSON_LISTINGS_FEED",
            FeedType.IMAGES: "JSON_LISTINGS_FEED"
        }
        return mapping.get(feed_type, "JSON_LISTINGS_FEED")