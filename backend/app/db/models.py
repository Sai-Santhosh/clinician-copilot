"""SQLAlchemy database models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    CLINICIAN = "clinician"
    VIEWER = "viewer"


class NoteStatus(str, Enum):
    """Status of a note version."""

    DRAFT = "draft"
    FINAL = "final"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=UserRole.CLINICIAN.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="created_by", foreign_keys="Session.created_by_user_id"
    )
    note_versions: Mapped[List["NoteVersion"]] = relationship(
        "NoteVersion", back_populates="created_by"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="actor")


class Patient(Base):
    """Patient model."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dob: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="patient")

    __table_args__ = (Index("ix_patients_name", "name"),)


class Session(Base):
    """Therapy session model with encrypted transcript."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    transcript_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    transcript_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # For audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="sessions")
    created_by: Mapped["User"] = relationship(
        "User", back_populates="sessions", foreign_keys=[created_by_user_id]
    )
    ai_suggestions: Mapped[List["AiSuggestion"]] = relationship(
        "AiSuggestion", back_populates="session"
    )
    note_versions: Mapped[List["NoteVersion"]] = relationship(
        "NoteVersion", back_populates="session"
    )

    __table_args__ = (
        Index("ix_sessions_patient_id", "patient_id"),
        Index("ix_sessions_created_at", "created_at"),
    )


class AiSuggestion(Base):
    """AI-generated suggestion storage."""

    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)  # Original AI output
    injection_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    gemini_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="ai_suggestions")

    __table_args__ = (Index("ix_ai_suggestions_session_id", "session_id"),)


class NoteVersion(Base):
    """Versioned clinical notes."""

    __tablename__ = "note_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NoteStatus.DRAFT.value
    )
    soap_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dx_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Diagnosis
    meds_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Medication education
    safety_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Safety plan
    ai_suggestion_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ai_suggestions.id"), nullable=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="note_versions")
    created_by: Mapped["User"] = relationship("User", back_populates="note_versions")

    __table_args__ = (
        Index("ix_note_versions_session_id", "session_id"),
        Index("ix_note_versions_status", "status"),
    )


class AuditLog(Base):
    """Immutable audit log for compliance."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    before_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    actor: Mapped["User"] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor", "actor_user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
