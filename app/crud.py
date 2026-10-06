from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from typing import Optional, List
from datetime import date

from app import models, schemas
from app.cache import invalidate_cache
from app.security import get_password_hash


# User CRUD
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate, role: str = "USER"):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        name=user.name, email=user.email, password_hash=hashed_password, role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Tags CRUD
def get_or_create_tag(db: Session, name: str):
    tag = db.query(models.Tag).filter(models.Tag.name == name).first()
    if not tag:
        tag = models.Tag(name=name)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    return tag


# Activity Log CRUD
def log_activity(
    db: Session,
    user_id: int,
    action: str,
    description: str,
    task_id: Optional[int] = None,
):
    activity = models.ActivityLog(
        user_id=user_id, task_id=task_id, action=action, description=description
    )
    db.add(activity)
    db.commit()
    return activity


def create_notification(
    db: Session, user_id: int, type: str, message: str, task_id: Optional[int] = None
):
    notification = models.Notification(
        user_id=user_id, task_id=task_id, type=type, message=message
    )
    db.add(notification)
    db.commit()
    return notification


# Task CRUD
def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def get_tasks(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    user_id: Optional[int] = None,
    due_date: Optional[date] = None,
    tag: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: Optional[str] = "asc",
):
    query = db.query(models.Task)

    if user_id is not None:
        query = query.filter(models.Task.user_id == user_id)

    if search:
        query = query.filter(
            or_(
                models.Task.title.ilike(f"%{search}%"),
                models.Task.description.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if due_date:
        query = query.filter(models.Task.due_date == due_date)
    if tag:
        query = query.join(models.Task.tags).filter(models.Tag.name == tag)

    if sort_by:
        sort_column = getattr(models.Task, sort_by, None)
        if sort_column:
            if order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(models.Task.created_at))

    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    return tasks, total


def get_overdue_tasks(db: Session, user_id: Optional[int] = None):
    today = date.today()
    query = db.query(models.Task).filter(
        models.Task.due_date < today, models.Task.status != "completed"
    )
    if user_id is not None:
        query = query.filter(models.Task.user_id == user_id)
    return query.all()


def create_task(db: Session, task: schemas.TaskCreate, user_id: int):
    db_task = models.Task(
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority.value,
        due_date=task.due_date,
        user_id=user_id,
    )

    db.add(db_task)

    if task.tags:
        for tag_name in task.tags:
            tag_obj = get_or_create_tag(db, tag_name)
            db_task.tags.append(tag_obj)

    db.commit()
    db.refresh(db_task)

    log_activity(
        db, user_id, "TASK_CREATED", f"Task '{db_task.title}' was created", db_task.id
    )
    create_notification(
        db,
        user_id,
        "TASK_CREATED",
        f"Task '{db_task.title}' has been created.",
        db_task.id,
    )

    invalidate_cache(f"dashboard_stats_{user_id}")
    invalidate_cache("dashboard_stats_admin")

    return db_task


def update_task(
    db: Session, db_task: models.Task, task: schemas.TaskUpdate, user_id: int
):
    changes = []

    if db_task.status != task.status.value:
        changes.append(f"status changed from {db_task.status} to {task.status.value}")
    if db_task.priority != task.priority.value:
        changes.append(
            f"priority changed from {db_task.priority} to {task.priority.value}"
        )
    if db_task.title != task.title:
        changes.append(f"title changed to '{task.title}'")
    if db_task.due_date != task.due_date:
        changes.append(f"due date changed from {db_task.due_date} to {task.due_date}")

    db_task.title = task.title
    db_task.description = task.description
    db_task.status = task.status.value
    db_task.priority = task.priority.value
    db_task.due_date = task.due_date

    if task.tags is not None:
        db_task.tags.clear()
        for tag_name in task.tags:
            tag_obj = get_or_create_tag(db, tag_name)
            db_task.tags.append(tag_obj)

    db.commit()
    db.refresh(db_task)

    if changes:
        log_activity(db, user_id, "TASK_UPDATED", ", ".join(changes), db_task.id)
        for change in changes:
            if change.startswith("status"):
                log_activity(db, user_id, "STATUS_CHANGED", change, db_task.id)
                if task.status.value == "completed":
                    create_notification(
                        db,
                        user_id,
                        "TASK_COMPLETED",
                        f"Task '{db_task.title}' has been completed.",
                        db_task.id,
                    )
            elif change.startswith("priority"):
                log_activity(db, user_id, "PRIORITY_CHANGED", change, db_task.id)

        invalidate_cache(f"dashboard_stats_{user_id}")
        invalidate_cache("dashboard_stats_admin")

    return db_task


def delete_task(db: Session, db_task: models.Task, user_id: int):
    task_id = db_task.id
    task_title = db_task.title
    db.delete(db_task)
    db.commit()
    log_activity(
        db, user_id, "TASK_DELETED", f"Task '{task_title}' was deleted", task_id
    )

    invalidate_cache(f"dashboard_stats_{user_id}")
    invalidate_cache("dashboard_stats_admin")

    return True


# Dashboard
def get_dashboard_stats(db: Session, user_id: Optional[int] = None):
    query = db.query(models.Task)
    if user_id:
        query = query.filter(models.Task.user_id == user_id)

    total_tasks = query.count()
    pending = query.filter(models.Task.status == "pending").count()
    in_progress = query.filter(models.Task.status == "in_progress").count()
    completed = query.filter(models.Task.status == "completed").count()
    high_priority = query.filter(models.Task.priority == "high").count()

    today = date.today()
    overdue = query.filter(
        models.Task.due_date < today, models.Task.status != "completed"
    ).count()

    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending,
        "in_progress_tasks": in_progress,
        "completed_tasks": completed,
        "high_priority_tasks": high_priority,
        "overdue_tasks": overdue,
    }
