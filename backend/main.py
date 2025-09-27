from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uvicorn
import os
from typing import List, Optional

from models.database import Base, engine
from routers import auth, feeds, users, credentials
from services.database import get_db
from services.auth import verify_token
from utils.logger import setup_logger

# Inicjalizacja loggera
logger = setup_logger()

# Tworzenie tabel
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Amazon Feed Migration SaaS",
    description="Migrate legacy Amazon feeds (XLSB/XML) to Amazon SP-API JSON format",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(credentials.router, prefix="/api/credentials", tags=["Credentials"])
app.include_router(feeds.router, prefix="/api/feeds", tags=["Feeds"])

@app.get("/")
async def root():
    return {"message": "Amazon Feed Migration SaaS API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "amazon-feed-migration-saas"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )