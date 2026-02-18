"""Note version schemas."""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict


class NoteVersionCreate(BaseModel):
    """Schema for creating a note version."""

    soap_json: Optional[str] = None
    dx_json: Optional[str] = None
    meds_json: Optional[str] = None
    safety_json: Optional[str] = None


class NoteVersionUpdate(BaseModel):
    """Schema for updating a note version."""

    soap_json: Optional[str] = Field(None, description="SOAP note JSON")
    dx_json: Optional[str] = Field(None, description="Diagnosis JSON")
    meds_json: Optional[str] = Field(None, description="Medication education JSON")
    safety_json: Optional[str] = Field(None, description="Safety plan JSON")


class NoteVersionResponse(BaseModel):
    """Schema for note version response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    version_number: int
    status: str
    soap_json: Optional[str] = None
    dx_json: Optional[str] = None
    meds_json: Optional[str] = None
    safety_json: Optional[str] = None
    ai_suggestion_id: Optional[int] = None
    created_by_user_id: int
    created_at: datetime


class NoteVersionListResponse(BaseModel):
    """Schema for listing note versions."""

    versions: list[NoteVersionResponse]
    total: int


class RollbackRequest(BaseModel):
    """Request to rollback to a previous version."""

    target_version_id: int = Field(..., description="Version ID to rollback to")
