from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.limiter import limiter
from app.database import Base, engine, get_db
from app.routers import tasks, auth, users, dashboard, notifications
from app.cache import redis_client
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import Depends

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")

app = FastAPI(
    title="Task Management REST API",
    description="A RESTful API for managing tasks with CRUD operations, search, filtering, validation, and persistent database storage.",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be adjusted safely for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(notifications.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"success": True, "message": "API is healthy", "data": {"status": "healthy"}}


@app.get("/health/db", tags=["health"])
def health_check_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "success": True,
            "message": "Database is healthy",
            "data": {"status": "healthy"},
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Database is unhealthy",
                "data": {"error": str(e)},
            },
        )


@app.get("/health/redis", tags=["health"])
def health_check_redis():
    try:
        if redis_client and redis_client.ping():
            return {
                "success": True,
                "message": "Redis is healthy",
                "data": {"status": "healthy"},
            }
        else:
            raise Exception("Redis ping failed or client not initialized")
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Redis is unhealthy",
                "data": {"error": str(e)},
            },
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Validation error", "data": None},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # Check if it's the general 404 Not Found or specifically task not found
        message = "Task not found" if exc.detail == "Task not found" else "Not found"
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": message, "data": None},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "data": None},
    )
