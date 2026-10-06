import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.limiter import limiter

# Disable rate limiting for tests
limiter.enabled = False

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_task_management.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers():
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepassword123",
        },
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    # Create an admin user manually in DB
    db = TestingSessionLocal()
    from app.models import User
    from app.security import get_password_hash

    admin = User(
        name="Admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpass123"),
        role="ADMIN",
    )
    db.add(admin)
    db.commit()
    db.close()

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_register_and_login():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "New User",
            "email": "new@example.com",
            "password": "newpassword123",
        },
    )
    assert response.status_code == 201

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": "newpassword123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


def test_create_task(auth_headers):
    response = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={
            "title": "Complete API assignment",
            "description": "Build and test the Task Management API",
            "status": "pending",
            "priority": "high",
            "due_date": "2026-10-15",
            "tags": ["python", "fastapi"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Task created successfully"
    assert data["data"]["title"] == "Complete API assignment"
    assert data["data"]["status"] == "pending"
    assert data["data"]["priority"] == "high"
    assert "id" in data["data"]
    assert len(data["data"]["tags"]) == 2


def test_create_task_invalid_status(auth_headers):
    response = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Invalid status task", "status": "started", "priority": "high"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["message"] == "Validation error"


def test_get_all_tasks(auth_headers):
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Test task", "status": "pending", "priority": "low"},
    )

    response = client.get("/api/v1/tasks", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    assert "pagination" in data
    assert data["pagination"]["total"] >= 1


def test_get_task_by_id(auth_headers):
    create_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Specific Task", "status": "pending", "priority": "medium"},
    )
    task_id = create_resp.json()["data"]["id"]

    response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Specific Task"


def test_get_nonexistent_task(auth_headers):
    response = client.get("/api/v1/tasks/9999", headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["message"] == "Task not found"


def test_update_task(auth_headers):
    create_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Old Title", "status": "pending", "priority": "low"},
    )
    task_id = create_resp.json()["data"]["id"]

    response = client.put(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"title": "New Title", "status": "in_progress", "priority": "high"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["title"] == "New Title"
    assert data["data"]["status"] == "in_progress"
    assert data["data"]["priority"] == "high"


def test_delete_task(auth_headers):
    create_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "To be deleted", "status": "pending", "priority": "low"},
    )
    task_id = create_resp.json()["data"]["id"]

    response = client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200

    get_resp = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_search_tasks(auth_headers):
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Apple API", "status": "pending", "priority": "low"},
    )
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Banana", "status": "pending", "priority": "low"},
    )

    response = client.get("/api/v1/tasks?search=API", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert "Apple API" in data[0]["title"]


def test_filter_by_status_and_priority(auth_headers):
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Task 1", "status": "pending", "priority": "high"},
    )
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Task 2", "status": "completed", "priority": "high"},
    )
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Task 3", "status": "pending", "priority": "low"},
    )

    resp1 = client.get("/api/v1/tasks?status=pending", headers=auth_headers)
    assert len(resp1.json()["data"]) == 2

    resp2 = client.get("/api/v1/tasks?priority=high", headers=auth_headers)
    assert len(resp2.json()["data"]) == 2

    resp3 = client.get(
        "/api/v1/tasks?status=pending&priority=high", headers=auth_headers
    )
    assert len(resp3.json()["data"]) == 1
    assert resp3.json()["data"][0]["title"] == "Task 1"


def test_pagination(auth_headers):
    for i in range(15):
        client.post(
            "/api/v1/tasks",
            headers=auth_headers,
            json={"title": f"Task {i}", "status": "pending", "priority": "low"},
        )

    resp1 = client.get("/api/v1/tasks?page=1&limit=10", headers=auth_headers)
    data1 = resp1.json()
    assert len(data1["data"]) == 10
    assert data1["pagination"]["total"] == 15
    assert data1["pagination"]["total_pages"] == 2

    resp2 = client.get("/api/v1/tasks?page=2&limit=10", headers=auth_headers)
    assert len(resp2.json()["data"]) == 5


def test_user_separation(auth_headers):
    # auth_headers user creates a task
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "User 1 Task", "status": "pending", "priority": "low"},
    )

    # Create User 2
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "User 2",
            "email": "user2@example.com",
            "password": "password123",
        },
    )
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "user2@example.com", "password": "password123"},
    )
    auth2 = {"Authorization": f"Bearer {resp2.json()['data']['access_token']}"}

    # User 2 list tasks should be empty
    get_resp = client.get("/api/v1/tasks", headers=auth2)
    assert len(get_resp.json()["data"]) == 0


def test_activity_log(auth_headers):
    create_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Tracked Task", "status": "pending", "priority": "low"},
    )
    task_id = create_resp.json()["data"]["id"]

    client.put(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"title": "Tracked Task", "status": "completed", "priority": "low"},
    )

    act_resp = client.get(f"/api/v1/tasks/{task_id}/activity", headers=auth_headers)
    activities = act_resp.json()["data"]
    assert len(activities) >= 2  # CREATE + UPDATE (and maybe STATUS_CHANGED)

    actions = [a["action"] for a in activities]
    assert "TASK_CREATED" in actions
    assert "TASK_UPDATED" in actions
    assert "STATUS_CHANGED" in actions


def test_dashboard_stats(auth_headers):
    client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Task", "status": "pending", "priority": "high"},
    )
    resp = client.get("/api/v1/dashboard", headers=auth_headers)
    stats = resp.json()["data"]
    assert stats["total_tasks"] == 1
    assert stats["high_priority_tasks"] == 1
