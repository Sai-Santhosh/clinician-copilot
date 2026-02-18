"""Audit log schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int
    action: str
    entity_type: str
    entity_id: int
    before_hash: Optional[str] = None
    after_hash: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Schema for listing audit logs."""

    logs: List[AuditLogResponse]
    total: int


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""

    actor_user_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    action: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
