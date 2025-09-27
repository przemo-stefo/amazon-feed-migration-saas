from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class FeedTypeEnum(str, Enum):
    INVENTORY = "inventory"
    PRICING = "pricing"
    LISTINGS = "listings"
    IMAGES = "images"

class FeedStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FeedCreateRequest(BaseModel):
    name: str
    feed_type: FeedTypeEnum

class FeedResponse(BaseModel):
    id: int
    name: str
    feed_type: FeedTypeEnum
    status: FeedStatusEnum
    original_filename: str
    file_size: Optional[int]
    total_items: Optional[int]
    processed_items: Optional[int]
    successful_items: Optional[int]
    failed_items: Optional[int]
    amazon_feed_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True

class FeedItemResponse(BaseModel):
    id: int
    sku: str
    asin: Optional[str]
    title: Optional[str]
    status: FeedStatusEnum
    original_data: Optional[Dict[str, Any]]
    mapped_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    amazon_item_id: Optional[str]
    amazon_response: Optional[Dict[str, Any]]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True

class FeedLogResponse(BaseModel):
    id: int
    level: str
    message: str
    details: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class FeedStatsResponse(BaseModel):
    total_feeds: int
    completed_feeds: int
    processing_feeds: int
    failed_feeds: int
    pending_feeds: int
    total_items_processed: int