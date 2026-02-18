"""Patient schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""

    name: str = Field(..., min_length=1, max_length=255)
    external_id: Optional[str] = Field(None, max_length=100)
    dob: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    external_id: Optional[str] = Field(None, max_length=100)
    dob: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PatientResponse(BaseModel):
    """Schema for patient response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    external_id: Optional[str] = None
    dob: Optional[str] = None
    created_at: datetime
