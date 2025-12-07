"""FastAPI application entry point."""
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.database import engine, Base, SessionLocal
from app.core.logging_config import logger
from app.api.v1.router import api_router
from app.services.cache import ACTIVE_POLICY_CACHE
from app import crud
import time

# Initialize logging
logger.info("Starting Permissions-as-Data Hybrid Service")

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database tables: {e}")
    raise

# Initialize FastAPI app
app = FastAPI(
    title="Permissions-as-Data Hybrid Service",
    description="A high-performance authorization engine with RBAC and ABAC support",
    version="1.0.0"
)

# Include API routes (without prefix for backward compatibility with existing tests)
app.include_router(api_router)
logger.info("API routes registered successfully")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Application shutting down")


@app.get("/", tags=["Health"])
def read_root():
    """Basic health check endpoint."""
    return {"status": "Permissions Service is Operational", "docs": "/docs"}


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check():
    """Detailed health check endpoint with system status."""
    health_status = {
        "status": "healthy",
        "service": "Permissions-as-Data Hybrid Service",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database connectivity check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        logger.error(f"Database health check failed: {e}")
    
    # Cache status check
    try:
        cached_policy = ACTIVE_POLICY_CACHE.get("policy")
        health_status["checks"]["cache"] = {
            "status": "healthy",
            "message": "Cache operational",
            "has_active_policy": cached_policy is not None
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["cache"] = {
            "status": "unhealthy",
            "message": f"Cache check failed: {str(e)}"
        }
        logger.error(f"Cache health check failed: {e}")
    
    # Active policy check
    try:
        db = SessionLocal()
        active_policy = crud.get_active_policy(db)
        db.close()
        health_status["checks"]["policy"] = {
            "status": "healthy" if active_policy else "warning",
            "message": "Active policy found" if active_policy else "No active policy configured",
            "policy_id": active_policy.id if active_policy else None
        }
    except Exception as e:
        health_status["checks"]["policy"] = {
            "status": "error",
            "message": f"Policy check failed: {str(e)}"
        }
        logger.error(f"Policy health check failed: {e}")
    
    # Return appropriate status code
    status_code = status.HTTP_200_OK
    if health_status["status"] == "degraded":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=health_status, status_code=status_code)

