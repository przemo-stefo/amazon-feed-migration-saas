import asyncio
from celery import Celery
from sqlalchemy.orm import Session
from datetime import datetime
import json
import traceback
from loguru import logger

from models.database import Feed, FeedItem, FeedLog, FeedStatus, AmazonCredentials
from services.database import SessionLocal
from services.excel_parser import ExcelParserService
from services.data_mapper import DataMapperService
from services.amazon_api import AmazonSPAPIService

# Konfiguracja Celery
celery_app = Celery(
    "amazon_feed_processor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "tasks.feed_processing.*": {"queue": "feed_processing"}
    }
)

@celery_app.task(bind=True, max_retries=3)
def process_feed_task(self, feed_id: int):
    """
    Główne zadanie Celery do przetwarzania feedów
    """
    db = SessionLocal()
    try:
        # Pobranie feeda z bazy danych
        feed = db.query(Feed).filter(Feed.id == feed_id).first()
        if not feed:
            logger.error(f"Feed {feed_id} not found")
            return {"error": "Feed not found"}

        # Aktualizacja statusu na "processing"
        feed.status = FeedStatus.PROCESSING
        feed.started_at = datetime.utcnow()
        db.commit()

        # Logowanie rozpoczęcia procesu
        _log_feed_message(db, feed_id, "INFO", "Starting feed processing")

        # Krok 1: Parsowanie pliku Excel/XLSB
        logger.info(f"Parsing file for feed {feed_id}")
        parsed_data = _parse_excel_file(db, feed)

        # Krok 2: Mapowanie danych
        logger.info(f"Mapping data for feed {feed_id}")
        mapped_data = _map_data_to_amazon_format(db, feed, parsed_data)

        # Krok 3: Wysłanie do Amazon SP-API
        logger.info(f"Submitting to Amazon SP-API for feed {feed_id}")
        amazon_feed_id = asyncio.run(_submit_to_amazon(db, feed, mapped_data))

        # Krok 4: Aktualizacja statusu i zapisanie wyników
        feed.amazon_feed_id = amazon_feed_id
        feed.status = FeedStatus.COMPLETED
        feed.completed_at = datetime.utcnow()
        feed.successful_items = len(mapped_data.get("messages", []))
        db.commit()

        _log_feed_message(db, feed_id, "INFO", f"Feed processing completed successfully. Amazon Feed ID: {amazon_feed_id}")

        return {
            "status": "success",
            "amazon_feed_id": amazon_feed_id,
            "processed_items": feed.successful_items
        }

    except Exception as e:
        logger.error(f"Feed processing failed for feed {feed_id}: {str(e)}")
        logger.error(traceback.format_exc())

        # Aktualizacja statusu na "failed"
        feed.status = FeedStatus.FAILED
        feed.error_message = str(e)
        feed.completed_at = datetime.utcnow()
        db.commit()

        _log_feed_message(db, feed_id, "ERROR", f"Feed processing failed: {str(e)}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying feed {feed_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {"error": str(e)}

    finally:
        db.close()

def _parse_excel_file(db: Session, feed: Feed) -> list:
    """
    Parsowanie pliku Excel/XLSB
    """
    try:
        parser = ExcelParserService()
        parsed_data = parser.parse_file(feed.file_path, feed.feed_type)

        # Walidacja danych
        validation_result = parser.validate_data(parsed_data, feed.feed_type)

        # Aktualizacja statystyk w bazie
        feed.total_items = validation_result["total_items"]
        feed.processed_items = validation_result["valid_items"]
        feed.failed_items = validation_result["invalid_items"]
        db.commit()

        # Zapisanie FeedItem dla każdego elementu
        for item_data in parsed_data:
            feed_item = FeedItem(
                feed_id=feed.id,
                sku=item_data.get("sku", ""),
                original_data=item_data,
                status=FeedStatus.PENDING
            )
            db.add(feed_item)

        db.commit()

        _log_feed_message(
            db, feed.id, "INFO",
            f"Parsed {validation_result['valid_items']} valid items out of {validation_result['total_items']} total items"
        )

        if validation_result["errors"]:
            error_details = {"validation_errors": validation_result["errors"][:10]}  # Pierwsze 10 błędów
            _log_feed_message(
                db, feed.id, "WARNING",
                f"Found {len(validation_result['errors'])} validation errors",
                error_details
            )

        return parsed_data

    except Exception as e:
        _log_feed_message(db, feed.id, "ERROR", f"Excel parsing failed: {str(e)}")
        raise

def _map_data_to_amazon_format(db: Session, feed: Feed, parsed_data: list) -> dict:
    """
    Mapowanie danych do formatu Amazon SP-API
    """
    try:
        # Pobranie credentials użytkownika
        credentials = db.query(AmazonCredentials).filter(
            AmazonCredentials.user_id == feed.user_id,
            AmazonCredentials.is_active == True
        ).first()

        if not credentials:
            raise Exception("Amazon credentials not found for user")

        mapper = DataMapperService()
        mapped_data = mapper.map_data(parsed_data, feed.feed_type, credentials.seller_id)

        # Walidacja zmapowanych danych
        validation_result = mapper.validate_mapped_data(mapped_data, feed.feed_type)

        # Aktualizacja FeedItem z zmapowanymi danymi
        messages = validation_result["mapped_data"]["messages"]
        feed_items = db.query(FeedItem).filter(FeedItem.feed_id == feed.id).all()

        for feed_item in feed_items:
            # Znajdź odpowiadającą wiadomość
            matching_message = next((msg for msg in messages if msg["sku"] == feed_item.sku), None)
            if matching_message:
                feed_item.mapped_data = matching_message
                feed_item.status = FeedStatus.PROCESSING
            else:
                feed_item.status = FeedStatus.FAILED
                feed_item.error_message = "Failed to map data"

        db.commit()

        _log_feed_message(
            db, feed.id, "INFO",
            f"Successfully mapped {validation_result['valid_messages']} out of {validation_result['total_messages']} items"
        )

        if validation_result["errors"]:
            error_details = {"mapping_errors": validation_result["errors"][:10]}
            _log_feed_message(
                db, feed.id, "WARNING",
                f"Found {len(validation_result['errors'])} mapping errors",
                error_details
            )

        return validation_result["mapped_data"]

    except Exception as e:
        _log_feed_message(db, feed.id, "ERROR", f"Data mapping failed: {str(e)}")
        raise

async def _submit_to_amazon(db: Session, feed: Feed, mapped_data: dict) -> str:
    """
    Wysłanie danych do Amazon SP-API
    """
    try:
        # Pobranie credentials
        credentials = db.query(AmazonCredentials).filter(
            AmazonCredentials.user_id == feed.user_id,
            AmazonCredentials.is_active == True
        ).first()

        if not credentials:
            raise Exception("Amazon credentials not found")

        # Inicjalizacja serwisu Amazon SP-API
        amazon_service = AmazonSPAPIService(credentials)

        # Konwersja mapped_data do JSON
        json_content = json.dumps(mapped_data, indent=2)

        # Utworzenie feed document
        doc_response = await amazon_service.create_feed_document("application/json")
        upload_url = doc_response["url"]
        document_id = doc_response["feedDocumentId"]

        _log_feed_message(
            db, feed.id, "INFO",
            f"Created feed document: {document_id}"
        )

        # Upload danych
        await amazon_service.upload_feed_document(upload_url, json_content, "application/json")

        _log_feed_message(
            db, feed.id, "INFO",
            "Successfully uploaded feed document"
        )

        # Utworzenie feeda
        feed_type_amazon = amazon_service.get_feed_type_mapping(feed.feed_type)
        feed_response = await amazon_service.create_feed(feed_type_amazon, document_id)

        amazon_feed_id = feed_response["feedId"]

        # Zapisanie amazon_feed_document_id
        feed.amazon_feed_document_id = document_id
        db.commit()

        _log_feed_message(
            db, feed.id, "INFO",
            f"Successfully submitted feed to Amazon SP-API: {amazon_feed_id}"
        )

        return amazon_feed_id

    except Exception as e:
        _log_feed_message(db, feed.id, "ERROR", f"Amazon SP-API submission failed: {str(e)}")
        raise

@celery_app.task
def check_feed_status_task(feed_id: int):
    """
    Zadanie do sprawdzania statusu feeda w Amazon SP-API
    """
    db = SessionLocal()
    try:
        feed = db.query(Feed).filter(Feed.id == feed_id).first()
        if not feed or not feed.amazon_feed_id:
            return {"error": "Feed not found or no Amazon feed ID"}

        # Pobranie credentials
        credentials = db.query(AmazonCredentials).filter(
            AmazonCredentials.user_id == feed.user_id,
            AmazonCredentials.is_active == True
        ).first()

        if not credentials:
            return {"error": "Amazon credentials not found"}

        # Sprawdzenie statusu
        amazon_service = AmazonSPAPIService(credentials)
        status_response = asyncio.run(amazon_service.get_feed_status(feed.amazon_feed_id))

        processing_status = status_response.get("processingStatus")

        _log_feed_message(
            db, feed.id, "INFO",
            f"Amazon feed status: {processing_status}"
        )

        # Aktualizacja statusu w bazie jeśli się zmienił
        if processing_status == "DONE":
            # Pobranie wyników feeda jeśli dostępne
            result_feed_document_id = status_response.get("resultFeedDocumentId")
            if result_feed_document_id:
                result_doc = asyncio.run(amazon_service.get_feed_result_document(result_feed_document_id))
                if result_doc.get("url"):
                    result_content = asyncio.run(amazon_service.download_feed_result(result_doc["url"]))
                    _log_feed_message(
                        db, feed.id, "INFO",
                        "Feed processing completed on Amazon",
                        {"amazon_result": result_content}
                    )

        elif processing_status == "FATAL":
            feed.status = FeedStatus.FAILED
            feed.error_message = "Feed processing failed on Amazon side"
            db.commit()

        return {"status": processing_status}

    except Exception as e:
        logger.error(f"Failed to check feed status for feed {feed_id}: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close()

def _log_feed_message(db: Session, feed_id: int, level: str, message: str, details: dict = None):
    """
    Pomocnicza funkcja do logowania wiadomości do bazy danych
    """
    try:
        feed_log = FeedLog(
            feed_id=feed_id,
            level=level,
            message=message,
            details=details
        )
        db.add(feed_log)
        db.commit()

        # Logowanie również do standardowego loggera
        if level == "ERROR":
            logger.error(f"Feed {feed_id}: {message}")
        elif level == "WARNING":
            logger.warning(f"Feed {feed_id}: {message}")
        else:
            logger.info(f"Feed {feed_id}: {message}")

    except Exception as e:
        logger.error(f"Failed to log message to database: {str(e)}")

# Konfiguracja scheduler'a dla sprawdzania statusów
@celery_app.task
def schedule_status_checks():
    """
    Okresowe sprawdzanie statusów feedów w toku
    """
    db = SessionLocal()
    try:
        # Znajdź feedy w statusie PROCESSING z amazon_feed_id
        feeds = db.query(Feed).filter(
            Feed.status == FeedStatus.PROCESSING,
            Feed.amazon_feed_id.isnot(None)
        ).all()

        for feed in feeds:
            check_feed_status_task.delay(feed.id)

        logger.info(f"Scheduled status checks for {len(feeds)} feeds")

    except Exception as e:
        logger.error(f"Failed to schedule status checks: {str(e)}")
    finally:
        db.close()

# Konfiguracja beat schedule (uruchamiaj co 5 minut)
celery_app.conf.beat_schedule = {
    'check-feed-statuses': {
        'task': 'tasks.feed_processing.schedule_status_checks',
        'schedule': 300.0,  # co 5 minut
    },
}
celery_app.conf.timezone = 'UTC'