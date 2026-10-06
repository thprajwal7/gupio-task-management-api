from fastapi import APIRouter, Depends
from app import models, schemas
from app.auth_deps import get_current_user

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


@router.get("/me", response_model=schemas.SuccessResponse[schemas.UserResponse])
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {
        "success": True,
        "message": "User profile retrieved successfully",
        "data": current_user,
    }
