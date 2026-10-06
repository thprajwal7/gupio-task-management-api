from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db
from app.auth_deps import get_current_user

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"],
)


@router.get(
    "",
    response_model=schemas.SuccessResponse[List[schemas.NotificationResponse]],
    summary="Get notifications",
)
def get_notifications(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    notifications = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "message": "Notifications retrieved successfully",
        "data": notifications,
    }


@router.patch(
    "/{notification_id}/read",
    response_model=schemas.SuccessResponse[schemas.NotificationResponse],
    summary="Mark notification as read",
)
def mark_notification_read(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return {
        "success": True,
        "message": "Notification marked as read",
        "data": notification,
    }
