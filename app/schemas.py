from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, TypeVar, Generic
from datetime import date, datetime
from enum import Enum


class StatusEnum(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RoleEnum(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


# User Schemas
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Tag Schemas
class TagResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# Task Schemas
class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: StatusEnum
    priority: PriorityEnum
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    tags: Optional[List[str]] = []


class TaskUpdate(TaskBase):
    tags: Optional[List[str]] = []


class TaskResponse(TaskBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Activity Log Schemas
class ActivityLogResponse(BaseModel):
    id: int
    user_id: int
    task_id: Optional[int]
    action: str
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Notification Schema
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    task_id: Optional[int]
    type: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Dashboard Schema
class DashboardStats(BaseModel):
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    high_priority_tasks: int
    overdue_tasks: int


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


# Generic Response Models
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    data: None = None


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: List[T]
    pagination: PaginationInfo
