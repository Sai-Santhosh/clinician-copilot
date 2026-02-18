"""AI generation schemas with strict typing for LLM outputs."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    """Citation referencing transcript evidence."""

    text: str = Field(..., max_length=150, description="Quoted snippet from transcript (<=25 words)")
    start_offset: Optional[int] = Field(None, description="Character offset start in transcript")
    end_offset: Optional[int] = Field(None, description="Character offset end in transcript")


class SOAPSection(BaseModel):
    """A section of the SOAP note with citations."""

    content: str = Field(..., description="Content of this section")
    citations: List[Citation] = Field(default_factory=list, description="Supporting evidence")


class SOAPNote(BaseModel):
    """SOAP note structure with citations."""

    subjective: SOAPSection = Field(..., description="Subjective section")
    objective: SOAPSection = Field(..., description="Objective section")
    assessment: SOAPSection = Field(..., description="Assessment section")
    plan: SOAPSection = Field(..., description="Plan section")


class DiagnosisItem(BaseModel):
    """A single diagnosis suggestion."""

    diagnosis: str = Field(..., description="Diagnosis name or ICD code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    rationale: str = Field(..., description="Brief rationale")
    citations: List[Citation] = Field(default_factory=list)


class DiagnosisSuggestion(BaseModel):
    """Diagnosis suggestions with confidence scores."""

    primary: Optional[DiagnosisItem] = Field(None, description="Primary diagnosis")
    differential: List[DiagnosisItem] = Field(
        default_factory=list, description="Differential diagnoses"
    )


class MedicationItem(BaseModel):
    """A medication education item."""

    medication: str = Field(..., description="Medication name")
    education: str = Field(..., description="Patient education content")
    warnings: List[str] = Field(default_factory=list, description="Key warnings")
    citations: List[Citation] = Field(default_factory=list)


class MedicationEducation(BaseModel):
    """Medication education content."""

    medications: List[MedicationItem] = Field(default_factory=list)
    general_guidance: Optional[str] = Field(None, description="General guidance")


class SafetyPlanItem(BaseModel):
    """Safety plan checklist item."""

    item: str = Field(..., description="Checklist item")
    completed: bool = Field(default=False)
    notes: Optional[str] = Field(None)
    citations: List[Citation] = Field(default_factory=list)


class SafetyPlan(BaseModel):
    """Safety plan checklist."""

    warning_signs: List[SafetyPlanItem] = Field(default_factory=list)
    coping_strategies: List[SafetyPlanItem] = Field(default_factory=list)
    support_contacts: List[SafetyPlanItem] = Field(default_factory=list)
    professional_contacts: List[SafetyPlanItem] = Field(default_factory=list)
    environment_safety: List[SafetyPlanItem] = Field(default_factory=list)
    reasons_for_living: List[SafetyPlanItem] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    """Request to generate AI suggestions."""

    prompt_version: str = Field(default="v1", pattern="^v[0-9]+$")
    model_name: Optional[str] = Field(None, description="Override default model")
    mode: str = Field(default="full", pattern="^(full|safe)$")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)


class GenerateResponse(BaseModel):
    """Response from AI generation."""

    ai_suggestion_id: int
    note_version_id: int
    injection_detected: bool = False
    safety_mode: bool = False
    warning_message: Optional[str] = None
    soap: SOAPNote
    diagnosis: DiagnosisSuggestion
    medications: MedicationEducation
    safety_plan: SafetyPlan
    gemini_latency_ms: int


class AiSuggestionResponse(BaseModel):
    """AI suggestion record response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    model_name: str
    prompt_version: str
    injection_flag: bool
    safety_mode: bool
    gemini_latency_ms: Optional[int]
    created_at: datetime


class AiOutputSchema(BaseModel):
    """Complete AI output schema for validation."""

    soap: SOAPNote
    diagnosis: DiagnosisSuggestion
    medications: MedicationEducation
    safety_plan: SafetyPlan
