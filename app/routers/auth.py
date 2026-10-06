from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
import logging
from app import crud, models, schemas
from app.database import get_db
from app.security import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from datetime import timedelta
from app.limiter import limiter

logger = logging.getLogger(__name__)


def send_welcome_email_background(email: str, name: str):
    # Simulate a time-consuming email sending process
    import time

    time.sleep(2)
    logger.info(f"BACKGROUND TASK: Welcome email successfully sent to {name} <{email}>")


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.post(
    "/register",
    response_model=schemas.SuccessResponse[schemas.UserResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def register_user(
    request: Request,
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = crud.create_user(db=db, user=user, role="USER")

    # Trigger background task
    background_tasks.add_task(
        send_welcome_email_background, new_user.email, new_user.name
    )

    return {
        "success": True,
        "message": "User registered successfully",
        "data": new_user,
    }


@router.post("/login", response_model=schemas.SuccessResponse[schemas.Token])
@limiter.limit("5/minute")
def login(
    request: Request, user_credentials: schemas.UserLogin, db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email=user_credentials.email)
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {
        "success": True,
        "message": "Login successful",
        "data": {"access_token": access_token, "token_type": "bearer"},
    }
