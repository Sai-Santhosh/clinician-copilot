"""Session schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class SessionCreate(BaseModel):
    """Schema for creating a new session."""

    transcript: str = Field(..., min_length=1, max_length=100000)


class SessionResponse(BaseModel):
    """Schema for session response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    created_by_user_id: int
    transcript_length: int  # Don't expose actual transcript
    created_at: datetime
    has_ai_suggestions: bool = False
    latest_version_id: Optional[int] = None
    latest_version_status: Optional[str] = None


class SessionListResponse(BaseModel):
    """Schema for listing sessions."""

    sessions: List[SessionResponse]
    total: int


class SessionDetailResponse(BaseModel):
    """Schema for session detail with decrypted transcript."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    created_by_user_id: int
    transcript: str  # Decrypted for authorized users
    created_at: datetime
