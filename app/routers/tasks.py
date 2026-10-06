from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import csv
import io
from sqlalchemy.orm import Session
from typing import Optional, List
from math import ceil
from datetime import date

from app import crud, models, schemas
from app.database import get_db
from app.auth_deps import get_current_user

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["tasks"],
)


@router.get(
    "/overdue",
    response_model=schemas.SuccessResponse[List[schemas.TaskResponse]],
    summary="Get overdue tasks",
)
def get_overdue_tasks(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user.role != "ADMIN" else None
    tasks = crud.get_overdue_tasks(db, user_id=user_id)
    return {
        "success": True,
        "message": "Overdue tasks retrieved successfully",
        "data": tasks,
    }


@router.post(
    "",
    response_model=schemas.SuccessResponse[schemas.TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
)
def create_task(
    task: schemas.TaskCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_task = crud.create_task(db=db, task=task, user_id=current_user.id)
    return {"success": True, "message": "Task created successfully", "data": db_task}


@router.get(
    "",
    response_model=schemas.PaginatedResponse[schemas.TaskResponse],
    summary="List tasks",
)
def read_tasks(
    search: Optional[str] = Query(
        None, description="Search tasks by title or description"
    ),
    status_filter: Optional[schemas.StatusEnum] = Query(
        None, alias="status", description="Filter tasks by status"
    ),
    priority: Optional[schemas.PriorityEnum] = Query(
        None, description="Filter tasks by priority"
    ),
    due_date: Optional[date] = Query(None, description="Filter tasks by due date"),
    tag: Optional[str] = Query(None, description="Filter tasks by tag"),
    sort_by: Optional[str] = Query(
        None,
        description="Sort tasks by field (created_at, updated_at, due_date, priority, title)",
    ),
    order: Optional[str] = Query("asc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * limit
    status_val = status_filter.value if status_filter else None
    priority_val = priority.value if priority else None
    user_id = current_user.id if current_user.role != "ADMIN" else None

    tasks, total = crud.get_tasks(
        db,
        skip=skip,
        limit=limit,
        search=search,
        status=status_val,
        priority=priority_val,
        user_id=user_id,
        due_date=due_date,
        tag=tag,
        sort_by=sort_by,
        order=order,
    )
    total_pages = ceil(total / limit) if total > 0 else 0

    return {
        "success": True,
        "message": "Tasks retrieved successfully",
        "data": tasks,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.get("/export/csv", summary="Export tasks as CSV")
def export_tasks_csv(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    tasks = crud.get_tasks(
        db,
        user_id=current_user.id if current_user.role != "ADMIN" else None,
        limit=1000,
    )[0]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Title",
            "Description",
            "Status",
            "Priority",
            "Due Date",
            "Created At",
            "Updated At",
        ]
    )

    for task in tasks:
        writer.writerow(
            [
                task.id,
                task.title,
                task.description or "",
                task.status,
                task.priority,
                task.due_date.isoformat() if task.due_date else "",
                task.created_at.isoformat() if task.created_at else "",
                task.updated_at.isoformat() if task.updated_at else "",
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks_export.csv"},
    )


@router.get(
    "/{task_id}",
    response_model=schemas.SuccessResponse[schemas.TaskResponse],
    summary="Get task",
)
def read_task(
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role != "ADMIN" and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {"success": True, "message": "Task retrieved successfully", "data": db_task}


@router.put(
    "/{task_id}",
    response_model=schemas.SuccessResponse[schemas.TaskResponse],
    summary="Update task",
)
def update_task(
    task_id: int,
    task: schemas.TaskUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role != "ADMIN" and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    db_task = crud.update_task(db, db_task=db_task, task=task, user_id=current_user.id)
    return {"success": True, "message": "Task updated successfully", "data": db_task}


@router.delete("/{task_id}", summary="Delete task")
def delete_task(
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role != "ADMIN" and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    crud.delete_task(db, db_task=db_task, user_id=current_user.id)
    return {"success": True, "message": "Task deleted successfully", "data": None}


@router.get(
    "/{task_id}/activity",
    response_model=schemas.SuccessResponse[List[schemas.ActivityLogResponse]],
    summary="Get task activity",
)
def get_task_activity(
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role != "ADMIN" and db_task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    activities = (
        db.query(models.ActivityLog)
        .filter(models.ActivityLog.task_id == task_id)
        .order_by(models.ActivityLog.created_at.desc())
        .all()
    )
    return {
        "success": True,
        "message": "Task activity retrieved successfully",
        "data": activities,
    }
