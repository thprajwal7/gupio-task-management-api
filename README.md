# Task Management REST API

## 1. Project Title
Task Management REST API

## 2. Problem Statement
Many professionals struggle to track tasks, prioritize their workload, and maintain productivity. This project provides a robust Backend Developer solution (Option 1) to securely manage users, authenticate sessions, create tasks, organize them by priority and status, and monitor activity through a comprehensive dashboard API.

## 3. Features
**Core Features:**
- Full CRUD for tasks (Create, Retrieve, Update, Delete)
- JWT Authentication & Role-Based Authorization (User/Admin)
- Advanced Querying: Search by title/description, filter by status/priority, sort, and paginate at the database layer.
- Overdue tasks tracking API
- Dashboard Statistics API
- Input Validation (Pydantic)
- Error Handling with consistent JSON formatting

**Bonus Features:**
- Redis Caching for Dashboard (with graceful PostgreSQL fallback)
- Data Export (Stream CSV output of tasks)
- Background Tasks (Mock async email welcome on registration)
- Rate Limiting (`slowapi` on login/register endpoints)
- Audit & Activity Logging for all task manipulations
- Comprehensive Health Checks (`/health`, `/health/db`, `/health/redis`)

## 4. Technology Stack
- **FastAPI** (Python web framework)
- **SQLAlchemy** (ORM)
- **PostgreSQL** (Production Database) & SQLite (Local testing)
- **Redis** (Caching)
- **Alembic** (Database Migrations)
- **JWT / Passlib** (Security & Hashing)
- **Pytest** (Automated Testing)
- **Docker & Docker Compose** (Containerization)
- **React/Vite** (Pre-existing Frontend Integration)

## 5. Architecture
The API utilizes a modern, clean n-tier architecture:
- **Routing Layer (`app/routers/`)**: Handles HTTP requests, validation, and endpoint security.
- **Service/Logic Layer (`app/crud.py`)**: Interacts directly with the database and triggers cache invalidations/background tasks.
- **Data Layer (`app/models.py`)**: SQLAlchemy models mapping Python objects to PostgreSQL tables.
- **Cache Layer (`app/cache.py`)**: Graceful wrapper around Redis.

## 6. Folder Structure
```
├── app/
│   ├── routers/ (tasks, auth, users, dashboard, notifications)
│   ├── models.py (SQLAlchemy DB models)
│   ├── schemas.py (Pydantic validation models)
│   ├── crud.py (Database operations)
│   ├── database.py (Engine & session config)
│   ├── security.py (JWT & Passwords)
│   ├── main.py (FastAPI entrypoint)
│   └── cache.py (Redis utility)
├── tests/
│   └── test_tasks.py (Pytest suite)
├── alembic/ (Migration scripts)
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 7. Database Setup
The API is configured to use PostgreSQL in production and local Docker setups. Alembic handles all schema generation.
To initialize the database locally without Docker, ensure PostgreSQL is running and execute:
```bash
alembic upgrade head
```

## 8. Environment Variables
Create a `.env` file in the root directory (refer to `.env.example`):
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/taskdb
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=supersecretkey
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 9. Local Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 10. Migration Commands
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 11. How to Run Backend
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 12. How to Run Frontend
*(Assuming frontend exists in `frontend/` directory)*
```bash
cd frontend
npm install
npm run dev
```

## 13. Authentication Flow
1. User calls `POST /api/v1/auth/register` with name, email, password.
2. User calls `POST /api/v1/auth/login` to receive an `access_token` (JWT).
3. Client attaches `Authorization: Bearer <token>` to all subsequent requests.
4. `get_current_user` dependency intercepts requests, decodes JWT, verifies expiration, and fetches the user from the DB.

## 14. API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login user |
| GET | `/api/v1/tasks` | List, search, filter, paginate tasks |
| POST | `/api/v1/tasks` | Create task |
| GET | `/api/v1/tasks/{id}` | Get task |
| PUT | `/api/v1/tasks/{id}` | Update task |
| DELETE| `/api/v1/tasks/{id}` | Delete task |
| GET | `/api/v1/tasks/export/csv`| Export tasks to CSV |
| GET | `/api/v1/dashboard` | Analytics (Redis Cached) |
| GET | `/health/db` | Health check |

## 15. Example Requests/Responses

**Create Task (POST `/api/v1/tasks`)**
*Request:*
```json
{
  "title": "Complete Gupio Assignment",
  "description": "Finalize REST API",
  "status": "pending",
  "priority": "high",
  "due_date": "2024-12-31"
}
```
*Response:*
```json
{
  "success": true,
  "message": "Task created successfully",
  "data": {
    "id": 1,
    "title": "Complete Gupio Assignment",
    "status": "pending",
    "priority": "high",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

## 16. Swagger URL
Navigate to: http://localhost:8000/docs
*(Click 'Authorize' at the top right to inject your JWT).*

## 17. Testing Instructions
Run the automated test suite (15 fully passing tests):
```bash
pytest
```

## 18. Docker Instructions
To run the entire stack (API + PostgreSQL + Redis):
```bash
docker-compose up --build -d
```

## 19. Deployment Instructions (Render + Neon PostgreSQL)
1. Push repository to GitHub.
2. Create a free PostgreSQL database on **Neon**. Copy the connection string.
3. In **Render**, create a new "Web Service" connected to your repo.
4. Set Build Command: `pip install -r requirements.txt && alembic upgrade head`
5. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables on Render: `DATABASE_URL` (from Neon), `SECRET_KEY`.

## 20. Verification Checklist
- [x] Create, Retrieve, Update, Delete tasks
- [x] PostgreSQL persistence
- [x] JWT Authentication & Role Authorization
- [x] Input Validation (422) & Error Handling (404, 500)
- [x] Database-level pagination, sorting, filtering
- [x] Automated Tests passing

## 21. Known Limitations
- Redis caching degrades gracefully to PostgreSQL if the Render instance cannot connect to a Redis cloud provider.

## 22. Future Improvements
- Soft Deletes (restorable tasks)
- Third-party OAuth integration (Google/GitHub login)
- API Keys for programmatic integration

---

# Examiner Verification
Please follow this exact sequence to verify the backend correctness:

1. **Open live API:** Navigate to the deployed API root (or `http://localhost:8000`).
2. **Open `/docs`:** Navigate to `/docs` to view the Swagger UI.
3. **Register:** Use `POST /api/v1/auth/register` to create an account.
4. **Login:** Use `POST /api/v1/auth/login` to retrieve your JWT token.
5. **Authorize:** Click the "Authorize" button in Swagger and paste your token.
6. **Create task:** Use `POST /api/v1/tasks` to create a task (e.g. status "pending", priority "high").
7. **Retrieve task:** Use `GET /api/v1/tasks/{id}` to fetch it.
8. **Update task:** Use `PUT /api/v1/tasks/{id}` to change the status to "completed".
9. **Search/filter task:** Use `GET /api/v1/tasks?status=completed&priority=high` and verify the results.
10. **Delete task:** Use `DELETE /api/v1/tasks/{id}` to remove it.
11. **Verify deleted task:** Call `GET /api/v1/tasks/{id}` again (Expect **404 Not Found**).
12. **Test invalid input:** Try creating a task with priority `"ultra"` (Expect **422 Validation Error**).
13. **Test missing record:** Try deleting task ID `99999` (Expect **404 Not Found**).
14. **Check dashboard:** Call `GET /api/v1/dashboard` and review the statistics.
15. **Check health endpoint:** Call `GET /health/db` to verify database connectivity.
