from fastapi import APIRouter
from src.configs.database import DatabaseManager

health_check_router = APIRouter(prefix="/health", tags=["Health"])


@health_check_router.get("/")
def health_check():
    """Health check endpoint"""
    db_health = DatabaseManager.health_check()
    return {
        "status": "healthy",
        "database": db_health
    }


@health_check_router.get("/live")
def liveness():
    """Liveness probe endpoint"""
    return {"status": "live"}


@health_check_router.get("/ready")
def readiness():
    """Readiness probe endpoint"""
    db_health = DatabaseManager.health_check()
    if db_health.get("status") == "healthy":
        return {"status": "ready"}
    return {"status": "not ready", "database": db_health}
