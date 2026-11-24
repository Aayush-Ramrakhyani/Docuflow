"""Central v1 API router — registers all endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    documents,
    extractions,
    organizations,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(documents.router)
api_router.include_router(extractions.router)
api_router.include_router(analytics.router)
