"""Main API router combining all route modules."""

from fastapi import APIRouter

from app.api.routes import auth, patients, sessions, notes, audit, health

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(notes.router, prefix="/notes", tags=["Notes"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(health.router, tags=["Health"])
