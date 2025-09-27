from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime

from models.database import Feed, FeedItem, FeedLog, FeedStatus, FeedType
from services.database import get_db
from services.auth import verify_token, get_current_user
from services.excel_parser import ExcelParserService
from services.amazon_api import AmazonSPAPIService
from tasks.feed_processing import process_feed_task
from schemas.feeds import FeedResponse, FeedCreateRequest, FeedItemResponse

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=FeedResponse)
async def upload_feed(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    feed_type: FeedType = FeedType.INVENTORY,
    feed_name: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload i przetwarzanie pliku Excel/XLSB z danymi feedów
    """
    # Walidacja typu pliku
    allowed_extensions = ['.xlsx', '.xlsb', '.xls']
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Generowanie unikalnej nazwy pliku
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Zapisanie pliku
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Utworzenie rekordu feed w bazie danych
    feed = Feed(
        user_id=current_user.id,
        name=feed_name or f"{feed_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        feed_type=feed_type,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        status=FeedStatus.PENDING
    )

    db.add(feed)
    db.commit()
    db.refresh(feed)

    # Dodanie zadania do kolejki w tle
    background_tasks.add_task(process_feed_task, feed.id)

    return FeedResponse.from_orm(feed)

@router.get("/", response_model=List[FeedResponse])
async def get_user_feeds(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Pobieranie listy feedów użytkownika
    """
    feeds = db.query(Feed).filter(
        Feed.user_id == current_user.id
    ).offset(skip).limit(limit).all()

    return [FeedResponse.from_orm(feed) for feed in feeds]

@router.get("/{feed_id}", response_model=FeedResponse)
async def get_feed(
    feed_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pobieranie szczegółów konkretnego feeda
    """
    feed = db.query(Feed).filter(
        Feed.id == feed_id,
        Feed.user_id == current_user.id
    ).first()

    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    return FeedResponse.from_orm(feed)

@router.get("/{feed_id}/items", response_model=List[FeedItemResponse])
async def get_feed_items(
    feed_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Pobieranie elementów feeda
    """
    # Sprawdzenie czy feed należy do użytkownika
    feed = db.query(Feed).filter(
        Feed.id == feed_id,
        Feed.user_id == current_user.id
    ).first()

    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    items = db.query(FeedItem).filter(
        FeedItem.feed_id == feed_id
    ).offset(skip).limit(limit).all()

    return [FeedItemResponse.from_orm(item) for item in items]

@router.post("/{feed_id}/retry")
async def retry_feed(
    feed_id: int,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ponowne przetwarzanie nieudanego feeda
    """
    feed = db.query(Feed).filter(
        Feed.id == feed_id,
        Feed.user_id == current_user.id
    ).first()

    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    if feed.status not in [FeedStatus.FAILED, FeedStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail="Only failed or cancelled feeds can be retried"
        )

    # Reset statusu
    feed.status = FeedStatus.PENDING
    feed.error_message = None
    db.commit()

    # Dodanie zadania do kolejki
    background_tasks.add_task(process_feed_task, feed.id)

    return {"message": "Feed retry initiated"}

@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Usunięcie feeda
    """
    feed = db.query(Feed).filter(
        Feed.id == feed_id,
        Feed.user_id == current_user.id
    ).first()

    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Usunięcie pliku
    try:
        if os.path.exists(feed.file_path):
            os.remove(feed.file_path)
    except Exception as e:
        # Log błędu, ale nie przerywaj operacji
        pass

    db.delete(feed)
    db.commit()

    return {"message": "Feed deleted successfully"}