"""Main API router that includes all v1 routes."""
from fastapi import APIRouter
from app.api.v1.routes import access, management

api_router = APIRouter()

api_router.include_router(access.router, tags=["access"])
api_router.include_router(management.router, tags=["management"])

