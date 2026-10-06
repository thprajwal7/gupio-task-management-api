from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.database import get_db
from app.auth_deps import get_current_user
from app.cache import get_cache, set_cache

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
)


@router.get("", response_model=schemas.SuccessResponse[schemas.DashboardStats])
def get_dashboard(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user.role != "ADMIN" else None

    cache_key = f"dashboard_stats_{user_id if user_id else 'admin'}"
    cached_stats = get_cache(cache_key)
    if cached_stats:
        return {
            "success": True,
            "message": "Dashboard retrieved from cache successfully",
            "data": cached_stats,
        }

    stats = crud.get_dashboard_stats(db, user_id=user_id)

    set_cache(cache_key, stats)

    return {
        "success": True,
        "message": "Dashboard retrieved successfully",
        "data": stats,
    }
