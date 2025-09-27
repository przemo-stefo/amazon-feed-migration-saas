from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from models.database import User
from services.database import get_db

# Konfiguracja
SECRET_KEY = "your-secret-key-here"  # W produkcji używaj zmiennej środowiskowej
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 dni

# Konfiguracja hashowania haseł
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

class AuthService:
    """
    Serwis obsługi uwierzytelniania i autoryzacji
    """

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Weryfikacja hasła
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hashowanie hasła
        """
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Tworzenie JWT access token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Weryfikacja JWT token
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return {"username": username}
        except JWTError:
            return None

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """
        Uwierzytelnianie użytkownika
        """
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()

        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        return user

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency do weryfikacji tokenu
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = AuthService.verify_token(token)
        if payload is None:
            raise credentials_exception
        return payload
    except Exception:
        raise credentials_exception

def get_current_user(
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
) -> User:
    """
    Dependency do pobierania aktualnego użytkownika
    """
    username = token_data.get("username")
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )

    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency do pobierania aktywnego użytkownika
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user