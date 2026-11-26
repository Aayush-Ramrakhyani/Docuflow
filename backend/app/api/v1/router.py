"""
Central v1 API router.

Aggregates every endpoint module under the /api/v1 prefix. main.py includes this
single router, so adding a new resource means importing it and registering it here.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    documents,
    extractions,
    organizations,
)

# Shared prefix — individual modules add their own sub-paths (e.g. /auth, /organizations)
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(documents.router)
api_router.include_router(extractions.router)
api_router.include_router(analytics.router)
