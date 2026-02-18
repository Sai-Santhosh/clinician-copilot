"""Pydantic schemas for API request/response models."""

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserCreate,
    UserResponse,
)
from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
)
from app.schemas.ai import (
    GenerateRequest,
    GenerateResponse,
    SOAPNote,
    DiagnosisSuggestion,
    MedicationEducation,
    SafetyPlan,
    Citation,
    AiSuggestionResponse,
)
from app.schemas.notes import (
    NoteVersionResponse,
    NoteVersionUpdate,
    NoteVersionCreate,
)
from app.schemas.audit import (
    AuditLogResponse,
    AuditLogFilter,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RefreshRequest",
    "RefreshResponse",
    "UserCreate",
    "UserResponse",
    # Patient
    "PatientCreate",
    "PatientResponse",
    "PatientUpdate",
    # Session
    "SessionCreate",
    "SessionResponse",
    "SessionListResponse",
    # AI
    "GenerateRequest",
    "GenerateResponse",
    "SOAPNote",
    "DiagnosisSuggestion",
    "MedicationEducation",
    "SafetyPlan",
    "Citation",
    "AiSuggestionResponse",
    # Notes
    "NoteVersionResponse",
    "NoteVersionUpdate",
    "NoteVersionCreate",
    # Audit
    "AuditLogResponse",
    "AuditLogFilter",
]
