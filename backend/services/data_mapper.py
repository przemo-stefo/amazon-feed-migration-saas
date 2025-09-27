from typing import Dict, Any, List, Optional
from enum import Enum
import re
from loguru import logger

from models.database import FeedType

class MappingRule:
    """
    Pojedyncza reguła mapowania danych
    """
    def __init__(self, source_field: str, target_field: str, transform_func: Optional[callable] = None, required: bool = False):
        self.source_field = source_field
        self.target_field = target_field
        self.transform_func = transform_func
        self.required = required

    def apply(self, source_data: Dict[str, Any]) -> Any:
        """
        Zastosowanie reguły mapowania
        """
        value = source_data.get(self.source_field)

        if value is None and self.required:
            raise ValueError(f"Required field '{self.source_field}' is missing")

        if value is not None and self.transform_func:
            try:
                value = self.transform_func(value)
            except Exception as e:
                logger.warning(f"Transform failed for field '{self.source_field}': {str(e)}")
                if self.required:
                    raise

        return value

class DataMapperService:
    """
    Serwis do mapowania danych z Excel/XLSB do formatu Amazon SP-API JSON
    """

    def __init__(self):
        self.mapping_rules = {
            FeedType.INVENTORY: self._get_inventory_mapping_rules(),
            FeedType.PRICING: self._get_pricing_mapping_rules(),
            FeedType.LISTINGS: self._get_listings_mapping_rules(),
            FeedType.IMAGES: self._get_images_mapping_rules()
        }

    def map_data(self, source_data: List[Dict[str, Any]], feed_type: FeedType, seller_id: str) -> Dict[str, Any]:
        """
        Główna metoda mapowania danych do formatu Amazon SP-API
        """
        try:
            if feed_type not in self.mapping_rules:
                raise ValueError(f"Unsupported feed type: {feed_type}")

            rules = self.mapping_rules[feed_type]
            mapped_messages = []

            for item in source_data:
                try:
                    mapped_item = self._map_single_item(item, rules, feed_type)
                    if mapped_item:
                        mapped_messages.append(mapped_item)
                except Exception as e:
                    logger.error(f"Failed to map item {item.get('sku', 'unknown')}: {str(e)}")
                    continue

            # Struktura zgodna z Amazon SP-API JSON_LISTINGS_FEED
            feed_document = {
                "header": {
                    "sellerId": seller_id,
                    "version": "2021-06-30",
                    "issueLocale": "en_US"
                },
                "messages": mapped_messages
            }

            logger.info(f"Successfully mapped {len(mapped_messages)} items for {feed_type.value} feed")
            return feed_document

        except Exception as e:
            logger.error(f"Data mapping failed: {str(e)}")
            raise

    def _map_single_item(self, source_item: Dict[str, Any], rules: List[MappingRule], feed_type: FeedType) -> Optional[Dict[str, Any]]:
        """
        Mapowanie pojedynczego elementu
        """
        sku = source_item.get('sku')
        if not sku:
            logger.warning("Skipping item without SKU")
            return None

        # Podstawowa struktura wiadomości
        message = {
            "messageId": str(sku),
            "sku": str(sku),
            "operationType": "UPDATE",
            "productType": "GENERIC",
            "attributes": {}
        }

        # Zastosowanie reguł mapowania
        for rule in rules:
            try:
                value = rule.apply(source_item)
                if value is not None:
                    self._set_nested_attribute(message["attributes"], rule.target_field, value)
            except Exception as e:
                logger.error(f"Failed to apply rule {rule.source_field} -> {rule.target_field}: {str(e)}")
                if rule.required:
                    return None

        return message

    def _set_nested_attribute(self, attributes: Dict[str, Any], path: str, value: Any):
        """
        Ustawienie zagnieżdżonej wartości w strukturze attributes
        """
        path_parts = path.split('.')
        current = attributes

        # Nawigacja do odpowiedniego miejsca w strukturze
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Ustawienie końcowej wartości
        final_key = path_parts[-1]
        current[final_key] = value

    def _get_inventory_mapping_rules(self) -> List[MappingRule]:
        """
        Reguły mapowania dla feeda inventory
        """
        return [
            MappingRule(
                source_field="sku",
                target_field="sku",
                required=True
            ),
            MappingRule(
                source_field="quantity",
                target_field="fulfillment_availability",
                transform_func=lambda x: [{"fulfillment_channel_code": "DEFAULT", "quantity": int(x) if x else 0}],
                required=True
            ),
            MappingRule(
                source_field="fulfillment_center_id",
                target_field="fulfillment_availability.0.fulfillment_channel_code",
                transform_func=lambda x: str(x) if x else "DEFAULT"
            )
        ]

    def _get_pricing_mapping_rules(self) -> List[MappingRule]:
        """
        Reguły mapowania dla feeda pricing
        """
        return [
            MappingRule(
                source_field="sku",
                target_field="sku",
                required=True
            ),
            MappingRule(
                source_field="price",
                target_field="purchasable_offer",
                transform_func=lambda x: [{
                    "currency": "USD",
                    "our_price": [{
                        "schedule": [{
                            "value_with_tax": float(x) if x else 0
                        }]
                    }]
                }],
                required=True
            ),
            MappingRule(
                source_field="currency",
                target_field="purchasable_offer.0.currency",
                transform_func=lambda x: str(x).upper() if x else "USD"
            ),
            MappingRule(
                source_field="sale_price",
                target_field="purchasable_offer.0.our_price.0.schedule.0.value_with_tax",
                transform_func=lambda x: float(x) if x and x != '' else None
            )
        ]

    def _get_listings_mapping_rules(self) -> List[MappingRule]:
        """
        Reguły mapowania dla feeda listings (produkty)
        """
        return [
            MappingRule(
                source_field="sku",
                target_field="sku",
                required=True
            ),
            MappingRule(
                source_field="title",
                target_field="item_name",
                transform_func=lambda x: [{"value": str(x), "language_tag": "en_US"}] if x else None,
                required=True
            ),
            MappingRule(
                source_field="description",
                target_field="description",
                transform_func=lambda x: [{"value": str(x), "language_tag": "en_US"}] if x else None
            ),
            MappingRule(
                source_field="brand",
                target_field="brand",
                transform_func=lambda x: [{"value": str(x)}] if x else None
            ),
            MappingRule(
                source_field="category",
                target_field="item_type_keyword",
                transform_func=lambda x: [{"value": str(x)}] if x else None
            ),
            MappingRule(
                source_field="price",
                target_field="purchasable_offer",
                transform_func=lambda x: [{
                    "currency": "USD",
                    "our_price": [{
                        "schedule": [{
                            "value_with_tax": float(x) if x else 0
                        }]
                    }]
                }] if x else None
            ),
            MappingRule(
                source_field="images",
                target_field="main_product_image_locator",
                transform_func=self._transform_images
            )
        ]

    def _get_images_mapping_rules(self) -> List[MappingRule]:
        """
        Reguły mapowania dla feeda images
        """
        return [
            MappingRule(
                source_field="sku",
                target_field="sku",
                required=True
            ),
            MappingRule(
                source_field="main_image",
                target_field="main_product_image_locator",
                transform_func=lambda x: [{"media_location": str(x)}] if x else None
            ),
            MappingRule(
                source_field="additional_images",
                target_field="other_product_image_locator",
                transform_func=self._transform_additional_images
            )
        ]

    def _transform_images(self, images_value: Any) -> Optional[List[Dict[str, str]]]:
        """
        Transformacja listy obrazów na format Amazon SP-API
        """
        if not images_value:
            return None

        if isinstance(images_value, str):
            # Jeśli to string, to najprawdopodobniej URL głównego obrazu
            return [{"media_location": images_value}]
        elif isinstance(images_value, list) and images_value:
            # Jeśli to lista, bierzemy pierwszy element jako główny obraz
            return [{"media_location": str(images_value[0])}]

        return None

    def _transform_additional_images(self, images_value: Any) -> Optional[List[Dict[str, str]]]:
        """
        Transformacja dodatkowych obrazów
        """
        if not images_value:
            return None

        images = []
        if isinstance(images_value, str):
            # Podział po przecinkach
            urls = [url.strip() for url in images_value.split(',') if url.strip()]
            images = [{"media_location": url} for url in urls]
        elif isinstance(images_value, list):
            images = [{"media_location": str(url)} for url in images_value if url]

        return images if images else None

    def validate_mapped_data(self, mapped_data: Dict[str, Any], feed_type: FeedType) -> Dict[str, Any]:
        """
        Walidacja zmapowanych danych
        """
        messages = mapped_data.get("messages", [])
        valid_messages = []
        errors = []

        for i, message in enumerate(messages):
            message_errors = []

            # Podstawowa walidacja
            if not message.get("sku"):
                message_errors.append("Missing SKU")

            if not message.get("messageId"):
                message_errors.append("Missing messageId")

            # Walidacja specyficzna dla typu feeda
            attributes = message.get("attributes", {})

            if feed_type == FeedType.INVENTORY:
                if not attributes.get("fulfillment_availability"):
                    message_errors.append("Missing fulfillment_availability")

            elif feed_type == FeedType.PRICING:
                if not attributes.get("purchasable_offer"):
                    message_errors.append("Missing purchasable_offer")

            elif feed_type == FeedType.LISTINGS:
                if not attributes.get("item_name"):
                    message_errors.append("Missing item_name")

            if not message_errors:
                valid_messages.append(message)
            else:
                errors.append({
                    "message_index": i,
                    "sku": message.get("sku", "unknown"),
                    "errors": message_errors
                })

        # Aktualizacja mapped_data z tylko prawidłowymi wiadomościami
        mapped_data["messages"] = valid_messages

        return {
            "total_messages": len(messages),
            "valid_messages": len(valid_messages),
            "invalid_messages": len(errors),
            "errors": errors[:50],  # Ograniczenie do 50 błędów
            "mapped_data": mapped_data
        }

    def get_sample_mapping(self, feed_type: FeedType) -> Dict[str, Any]:
        """
        Zwraca przykładowe mapowanie dla danego typu feeda
        """
        samples = {
            FeedType.INVENTORY: {
                "source_format": {
                    "sku": "PROD-001",
                    "quantity": 100,
                    "fulfillment_center_id": "DEFAULT"
                },
                "amazon_format": {
                    "messageId": "PROD-001",
                    "sku": "PROD-001",
                    "operationType": "UPDATE",
                    "productType": "GENERIC",
                    "attributes": {
                        "fulfillment_availability": [
                            {
                                "fulfillment_channel_code": "DEFAULT",
                                "quantity": 100
                            }
                        ]
                    }
                }
            },
            FeedType.PRICING: {
                "source_format": {
                    "sku": "PROD-001",
                    "price": 29.99,
                    "currency": "USD"
                },
                "amazon_format": {
                    "messageId": "PROD-001",
                    "sku": "PROD-001",
                    "operationType": "UPDATE",
                    "productType": "GENERIC",
                    "attributes": {
                        "purchasable_offer": [
                            {
                                "currency": "USD",
                                "our_price": [
                                    {
                                        "schedule": [
                                            {
                                                "value_with_tax": 29.99
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }

        return samples.get(feed_type, {})