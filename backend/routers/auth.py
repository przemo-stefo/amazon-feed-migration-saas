from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from models.database import User
from services.database import get_db
from services.auth import AuthService, get_current_user
from schemas.users import UserResponse, UserCreate

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Rejestracja nowego użytkownika
    """
    # Walidacja potwierdzenia hasła
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Sprawdzenie czy użytkownik już istnieje
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Walidacja siły hasła
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Utworzenie nowego użytkownika
    hashed_password = AuthService.get_password_hash(user_data.password)

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.from_orm(new_user)

@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Logowanie użytkownika
    """
    user = AuthService.authenticate_user(db, login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )

    # Utworzenie access token
    access_token = AuthService.create_access_token(
        data={"sub": user.username}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.post("/login/oauth", response_model=Token)
async def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Logowanie dla OAuth2 (kompatybilność z FastAPI docs)
    """
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = AuthService.create_access_token(
        data={"sub": user.username}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Pobieranie informacji o aktualnym użytkowniku
    """
    return UserResponse.from_orm(current_user)

@router.post("/logout")
async def logout():
    """
    Wylogowanie użytkownika (po stronie klienta należy usunąć token)
    """
    return {"message": "Successfully logged out"}

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    confirm_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Zmiana hasła użytkownika
    """
    # Weryfikacja aktualnego hasła
    if not AuthService.verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Walidacja nowego hasła
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # Aktualizacja hasła
    current_user.hashed_password = AuthService.get_password_hash(new_password)
    db.commit()

    return {"message": "Password changed successfully"}

@router.post("/request-password-reset")
async def request_password_reset(
    email: EmailStr,
    db: Session = Depends(get_db)
):
    """
    Żądanie resetu hasła (w pełnej implementacji wysłałoby email)
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Nie ujawniamy czy email istnieje w systemie
        return {"message": "If this email exists in our system, you will receive password reset instructions"}

    # W rzeczywistej implementacji:
    # 1. Generuj unikalny token reset
    # 2. Zapisz token w bazie z czasem wygaśnięcia
    # 3. Wyślij email z linkiem do resetu

    return {"message": "If this email exists in our system, you will receive password reset instructions"}

@router.post("/reset-password")
async def reset_password(
    reset_token: str,
    new_password: str,
    confirm_password: str,
    db: Session = Depends(get_db)
):
    """
    Reset hasła przy użyciu tokenu (uproszczona implementacja)
    """
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # W rzeczywistej implementacji:
    # 1. Weryfikuj token reset
    # 2. Sprawdź czy nie wygasł
    # 3. Znajdź użytkownika powiązanego z tokenem
    # 4. Zaktualizuj hasło
    # 5. Usuń lub oznacz token jako użyty

    return {"message": "Password reset successfully"}

@router.get("/validate-token")
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    Walidacja tokenu (używane przez frontend do sprawdzenia czy token jest ważny)
    """
    return {
        "valid": True,
        "user": UserResponse.from_orm(current_user)
    }