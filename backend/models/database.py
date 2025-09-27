from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class FeedStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FeedType(enum.Enum):
    INVENTORY = "inventory"
    PRICING = "pricing"
    LISTINGS = "listings"
    IMAGES = "images"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacje
    amazon_credentials = relationship("AmazonCredentials", back_populates="user")
    feeds = relationship("Feed", back_populates="user")

class AmazonCredentials(Base):
    __tablename__ = "amazon_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Amazon SP-API credentials
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=False)
    marketplace_id = Column(String(50), nullable=False)
    seller_id = Column(String(50), nullable=False)

    # AWS credentials
    aws_access_key = Column(String(255), nullable=False)
    aws_secret_key = Column(String(255), nullable=False)
    aws_region = Column(String(20), default="us-east-1")

    is_sandbox = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacje
    user = relationship("User", back_populates="amazon_credentials")

class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Feed metadata
    name = Column(String(255), nullable=False)
    feed_type = Column(Enum(FeedType), nullable=False)
    status = Column(Enum(FeedStatus), default=FeedStatus.PENDING)

    # File information
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)

    # Processing information
    total_items = Column(Integer)
    processed_items = Column(Integer, default=0)
    successful_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)

    # Amazon SP-API information
    amazon_feed_id = Column(String(255))
    amazon_feed_document_id = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Error handling
    error_message = Column(Text)

    # Relacje
    user = relationship("User", back_populates="feeds")
    feed_items = relationship("FeedItem", back_populates="feed")
    feed_logs = relationship("FeedLog", back_populates="feed")

class FeedItem(Base):
    __tablename__ = "feed_items"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("feeds.id"), nullable=False)

    # Item data
    sku = Column(String(100), nullable=False)
    asin = Column(String(20))
    title = Column(String(500))

    # Original data from Excel
    original_data = Column(JSON)

    # Mapped data for SP-API
    mapped_data = Column(JSON)

    # Processing status
    status = Column(Enum(FeedStatus), default=FeedStatus.PENDING)
    error_message = Column(Text)

    # Amazon response
    amazon_item_id = Column(String(255))
    amazon_response = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

    # Relacje
    feed = relationship("Feed", back_populates="feed_items")

class FeedLog(Base):
    __tablename__ = "feed_logs"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("feeds.id"), nullable=False)

    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    details = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacje
    feed = relationship("Feed", back_populates="feed_logs")

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)