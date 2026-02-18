"""Notes service for managing clinical documentation."""

import json
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import encrypt_data, decrypt_data, hash_for_audit
from app.db.models import Session, AiSuggestion, NoteVersion, NoteStatus
from app.schemas.ai import AiOutputSchema, GenerateResponse
from app.services.llm_client import LLMClient, get_llm_client
from app.services.guardrails import GuardrailsService
from app.services.audit import AuditService

logger = get_logger()


class NotesService:
    """Service for managing clinical notes and AI generation."""

    def __init__(
        self,
        db: AsyncSession,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize notes service.
        
        Args:
            db: Database session.
            llm_client: LLM client instance.
        """
        self.db = db
        self.llm_client = llm_client or get_llm_client()
        self.guardrails = GuardrailsService()
        self.audit = AuditService(db)

    async def generate_ai_suggestions(
        self,
        session_id: int,
        user_id: int,
        prompt_version: str = "v1",
        model_name: Optional[str] = None,
        mode: str = "full",
        temperature: float = 0.0,
    ) -> GenerateResponse:
        """Generate AI suggestions for a session.
        
        Args:
            session_id: Session ID to generate for.
            user_id: User requesting generation.
            prompt_version: Version of prompt template.
            model_name: Override model name.
            mode: 'full' or 'safe' mode.
            temperature: Generation temperature.
            
        Returns:
            GenerateResponse with AI suggestions.
        """
        # Get session with encrypted transcript
        session = await self.db.get(Session, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Decrypt transcript
        transcript = decrypt_data(session.transcript_encrypted)

        # Check for prompt injection
        injection_detected, patterns = self.guardrails.scan_for_injection(transcript)

        # Force safe mode if injection detected
        safe_mode = mode == "safe" or injection_detected
        warning_message = None

        if injection_detected:
            warning_message = (
                f"Potential prompt injection detected. "
                f"Running in safe mode. Patterns matched: {len(patterns)}"
            )
            logger.warning(
                "Injection detected, forcing safe mode",
                extra={"session_id": session_id, "pattern_count": len(patterns)},
            )

        # Generate AI output
        try:
            output, latency_ms = await self.llm_client.generate(
                transcript=transcript,
                temperature=temperature,
                safe_mode=safe_mode,
            )
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            # Create empty output on failure
            output = self.llm_client.create_empty_output()
            latency_ms = 0
            warning_message = f"AI generation failed: {str(e)}"

        # Store AI suggestion
        ai_suggestion = AiSuggestion(
            session_id=session_id,
            model_name=model_name or self.llm_client.model_name,
            prompt_version=prompt_version,
            raw_json=output.model_dump_json(),
            injection_flag=injection_detected,
            safety_mode=safe_mode,
            gemini_latency_ms=latency_ms,
        )
        self.db.add(ai_suggestion)
        await self.db.flush()

        # Create new draft version
        version = await self._create_version_from_ai(
            session_id=session_id,
            user_id=user_id,
            ai_suggestion_id=ai_suggestion.id,
            output=output,
        )

        return GenerateResponse(
            ai_suggestion_id=ai_suggestion.id,
            note_version_id=version.id,
            injection_detected=injection_detected,
            safety_mode=safe_mode,
            warning_message=warning_message,
            soap=output.soap,
            diagnosis=output.diagnosis,
            medications=output.medications,
            safety_plan=output.safety_plan,
            gemini_latency_ms=latency_ms,
        )

    async def _create_version_from_ai(
        self,
        session_id: int,
        user_id: int,
        ai_suggestion_id: int,
        output: AiOutputSchema,
    ) -> NoteVersion:
        """Create a new note version from AI output.
        
        Args:
            session_id: Session ID.
            user_id: User creating the version.
            ai_suggestion_id: Associated AI suggestion.
            output: Parsed AI output.
            
        Returns:
            Created NoteVersion.
        """
        # Get next version number
        result = await self.db.execute(
            select(func.max(NoteVersion.version_number))
            .where(NoteVersion.session_id == session_id)
        )
        max_version = result.scalar() or 0

        version = NoteVersion(
            session_id=session_id,
            version_number=max_version + 1,
            status=NoteStatus.DRAFT.value,
            soap_json=output.soap.model_dump_json(),
            dx_json=output.diagnosis.model_dump_json(),
            meds_json=output.medications.model_dump_json(),
            safety_json=output.safety_plan.model_dump_json(),
            ai_suggestion_id=ai_suggestion_id,
            created_by_user_id=user_id,
        )
        self.db.add(version)
        await self.db.flush()

        # Audit log
        await self.audit.log(
            actor_user_id=user_id,
            action="create_version",
            entity_type="note_version",
            entity_id=version.id,
            after_data=version.soap_json,
        )

        return version

    async def update_version(
        self,
        version_id: int,
        user_id: int,
        soap_json: Optional[str] = None,
        dx_json: Optional[str] = None,
        meds_json: Optional[str] = None,
        safety_json: Optional[str] = None,
    ) -> NoteVersion:
        """Update a draft note version.
        
        Args:
            version_id: Version to update.
            user_id: User making the update.
            soap_json: Updated SOAP JSON.
            dx_json: Updated diagnosis JSON.
            meds_json: Updated medication JSON.
            safety_json: Updated safety plan JSON.
            
        Returns:
            Updated NoteVersion.
        """
        version = await self.db.get(NoteVersion, version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        if version.status == NoteStatus.FINAL.value:
            raise ValueError("Cannot update a finalized version")

        # Store before state for audit
        before_data = {
            "soap": version.soap_json,
            "dx": version.dx_json,
            "meds": version.meds_json,
            "safety": version.safety_json,
        }

        # Update fields
        if soap_json is not None:
            version.soap_json = soap_json
        if dx_json is not None:
            version.dx_json = dx_json
        if meds_json is not None:
            version.meds_json = meds_json
        if safety_json is not None:
            version.safety_json = safety_json

        # Store after state for audit
        after_data = {
            "soap": version.soap_json,
            "dx": version.dx_json,
            "meds": version.meds_json,
            "safety": version.safety_json,
        }

        await self.audit.log(
            actor_user_id=user_id,
            action="update_version",
            entity_type="note_version",
            entity_id=version_id,
            before_data=json.dumps(before_data),
            after_data=json.dumps(after_data),
        )

        return version

    async def finalize_version(
        self,
        version_id: int,
        user_id: int,
    ) -> NoteVersion:
        """Finalize a draft version.
        
        Args:
            version_id: Version to finalize.
            user_id: User finalizing.
            
        Returns:
            Finalized NoteVersion.
        """
        version = await self.db.get(NoteVersion, version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        if version.status == NoteStatus.FINAL.value:
            raise ValueError("Version is already finalized")

        before_status = version.status
        version.status = NoteStatus.FINAL.value

        await self.audit.log(
            actor_user_id=user_id,
            action="finalize_version",
            entity_type="note_version",
            entity_id=version_id,
            before_data=json.dumps({"status": before_status}),
            after_data=json.dumps({"status": NoteStatus.FINAL.value}),
        )

        logger.info(
            f"Version {version_id} finalized by user {user_id}",
            extra={"version_id": version_id, "user_id": user_id},
        )

        return version

    async def rollback_to_version(
        self,
        session_id: int,
        target_version_id: int,
        user_id: int,
    ) -> NoteVersion:
        """Rollback to a previous version by creating a new version with old content.
        
        Args:
            session_id: Session ID.
            target_version_id: Version to rollback to.
            user_id: User performing rollback.
            
        Returns:
            New NoteVersion created from rollback.
        """
        target = await self.db.get(NoteVersion, target_version_id)
        if not target:
            raise ValueError(f"Target version {target_version_id} not found")

        if target.session_id != session_id:
            raise ValueError("Target version does not belong to this session")

        # Get next version number
        result = await self.db.execute(
            select(func.max(NoteVersion.version_number))
            .where(NoteVersion.session_id == session_id)
        )
        max_version = result.scalar() or 0

        # Create new version with old content
        new_version = NoteVersion(
            session_id=session_id,
            version_number=max_version + 1,
            status=NoteStatus.DRAFT.value,
            soap_json=target.soap_json,
            dx_json=target.dx_json,
            meds_json=target.meds_json,
            safety_json=target.safety_json,
            ai_suggestion_id=target.ai_suggestion_id,
            created_by_user_id=user_id,
        )
        self.db.add(new_version)
        await self.db.flush()

        await self.audit.log(
            actor_user_id=user_id,
            action="rollback_version",
            entity_type="note_version",
            entity_id=new_version.id,
            before_data=json.dumps({"source_version_id": target_version_id}),
            after_data=json.dumps({"new_version_number": new_version.version_number}),
        )

        return new_version
