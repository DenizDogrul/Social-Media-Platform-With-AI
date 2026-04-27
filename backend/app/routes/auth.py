from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.user import User
from app.auth import create_access_token, get_current_user
from app.services.rate_limit import apply_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    apply_rate_limit(request, bucket="auth_register", limit=15, window_seconds=60)
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = User(username=user_data.username, email=user_data.email)
    user.set_password(user_data.password)
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already registered")

    db.refresh(user)
    return {"id": user.id, "username": user.username, "email": user.email}


@router.post("/login")
def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    apply_rate_limit(request, bucket="auth_login", limit=10, window_seconds=60)
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not user.verify_password(user_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}
