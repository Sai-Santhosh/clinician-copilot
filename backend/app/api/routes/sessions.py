"""Session management routes."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, ClinicianOrAdmin, AnyAuthUser
from app.core.security import encrypt_data, decrypt_data, hash_for_audit
from app.db.models import Session, Patient, AiSuggestion, NoteVersion
from app.schemas.session import SessionCreate, SessionResponse, SessionListResponse
from app.schemas.ai import GenerateRequest, GenerateResponse, AiSuggestionResponse
from app.services.notes import NotesService
from app.services.audit import AuditService
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter()


@router.post(
    "/patients/{patient_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a session",
    description="Create a new therapy session with encrypted transcript. Requires clinician or admin role.",
)
async def create_session(
    patient_id: int,
    session_data: SessionCreate,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> SessionResponse:
    """Create a new therapy session.
    
    Args:
        patient_id: Patient ID.
        session_data: Session data including transcript.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Created session (without transcript).
    """
    # Verify patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Encrypt transcript
    transcript_encrypted = encrypt_data(session_data.transcript)
    transcript_hash = hash_for_audit(session_data.transcript)

    session = Session(
        patient_id=patient_id,
        created_by_user_id=current_user.id,
        transcript_encrypted=transcript_encrypted,
        transcript_hash=transcript_hash,
    )
    db.add(session)
    await db.flush()

    # Audit log (don't log transcript content)
    audit = AuditService(db)
    await audit.log(
        actor_user_id=current_user.id,
        action="create",
        entity_type="session",
        entity_id=session.id,
        after_data=f'{{"patient_id": {patient_id}, "transcript_length": {len(session_data.transcript)}}}',
    )

    logger.info(
        f"Session created for patient {patient_id}",
        extra={"session_id": session.id, "patient_id": patient_id},
    )

    return SessionResponse(
        id=session.id,
        patient_id=session.patient_id,
        created_by_user_id=session.created_by_user_id,
        transcript_length=len(session_data.transcript),
        created_at=session.created_at,
        has_ai_suggestions=False,
        latest_version_id=None,
        latest_version_status=None,
    )


@router.get(
    "/patients/{patient_id}/sessions",
    response_model=SessionListResponse,
    summary="List patient sessions",
    description="Get all sessions for a patient.",
)
async def list_patient_sessions(
    patient_id: int,
    db: DbSession,
    current_user: AnyAuthUser,
    skip: int = 0,
    limit: int = 100,
) -> SessionListResponse:
    """List sessions for a patient.
    
    Args:
        patient_id: Patient ID.
        db: Database session.
        current_user: Authenticated user.
        skip: Records to skip.
        limit: Maximum records.
        
    Returns:
        List of sessions.
    """
    # Verify patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Get sessions with related data
    query = (
        select(Session)
        .where(Session.patient_id == patient_id)
        .order_by(Session.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Get total count
    count_query = select(func.count(Session.id)).where(Session.patient_id == patient_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Build response with additional info
    response_sessions = []
    for session in sessions:
        # Get latest version
        version_query = (
            select(NoteVersion)
            .where(NoteVersion.session_id == session.id)
            .order_by(NoteVersion.version_number.desc())
            .limit(1)
        )
        version_result = await db.execute(version_query)
        latest_version = version_result.scalar_one_or_none()

        # Check for AI suggestions
        suggestions_query = select(func.count(AiSuggestion.id)).where(
            AiSuggestion.session_id == session.id
        )
        suggestions_result = await db.execute(suggestions_query)
        has_suggestions = (suggestions_result.scalar() or 0) > 0

        response_sessions.append(
            SessionResponse(
                id=session.id,
                patient_id=session.patient_id,
                created_by_user_id=session.created_by_user_id,
                transcript_length=len(session.transcript_encrypted),
                created_at=session.created_at,
                has_ai_suggestions=has_suggestions,
                latest_version_id=latest_version.id if latest_version else None,
                latest_version_status=latest_version.status if latest_version else None,
            )
        )

    return SessionListResponse(sessions=response_sessions, total=total)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session by ID",
    description="Get session details (without transcript).",
)
async def get_session(
    session_id: int,
    db: DbSession,
    current_user: AnyAuthUser,
) -> SessionResponse:
    """Get a session by ID.
    
    Args:
        session_id: Session ID.
        db: Database session.
        current_user: Authenticated user.
        
    Returns:
        Session details.
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Get latest version
    version_query = (
        select(NoteVersion)
        .where(NoteVersion.session_id == session.id)
        .order_by(NoteVersion.version_number.desc())
        .limit(1)
    )
    version_result = await db.execute(version_query)
    latest_version = version_result.scalar_one_or_none()

    # Check for AI suggestions
    suggestions_query = select(func.count(AiSuggestion.id)).where(
        AiSuggestion.session_id == session.id
    )
    suggestions_result = await db.execute(suggestions_query)
    has_suggestions = (suggestions_result.scalar() or 0) > 0

    # Decrypt transcript to get length
    transcript = decrypt_data(session.transcript_encrypted)

    return SessionResponse(
        id=session.id,
        patient_id=session.patient_id,
        created_by_user_id=session.created_by_user_id,
        transcript_length=len(transcript),
        created_at=session.created_at,
        has_ai_suggestions=has_suggestions,
        latest_version_id=latest_version.id if latest_version else None,
        latest_version_status=latest_version.status if latest_version else None,
    )


@router.get(
    "/{session_id}/transcript",
    summary="Get session transcript",
    description="Get decrypted transcript. Requires clinician or admin role.",
)
async def get_session_transcript(
    session_id: int,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> dict:
    """Get decrypted transcript for a session.
    
    Args:
        session_id: Session ID.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Decrypted transcript.
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    transcript = decrypt_data(session.transcript_encrypted)

    return {"transcript": transcript}


@router.post(
    "/{session_id}/generate",
    response_model=GenerateResponse,
    summary="Generate AI suggestions",
    description="Generate AI-powered clinical documentation suggestions. Requires clinician or admin role.",
)
async def generate_ai_suggestions(
    session_id: int,
    request: GenerateRequest,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> GenerateResponse:
    """Generate AI suggestions for a session.
    
    Args:
        session_id: Session ID.
        request: Generation parameters.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Generated AI suggestions.
    """
    # Verify session exists
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    notes_service = NotesService(db)

    try:
        response = await notes_service.generate_ai_suggestions(
            session_id=session_id,
            user_id=current_user.id,
            prompt_version=request.prompt_version,
            model_name=request.model_name,
            mode=request.mode,
            temperature=request.temperature,
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI generation failed. Please try again.",
        )


@router.get(
    "/{session_id}/suggestions",
    response_model=List[AiSuggestionResponse],
    summary="List AI suggestions",
    description="Get all AI suggestions for a session.",
)
async def list_session_suggestions(
    session_id: int,
    db: DbSession,
    current_user: AnyAuthUser,
) -> List[AiSuggestionResponse]:
    """List AI suggestions for a session.
    
    Args:
        session_id: Session ID.
        db: Database session.
        current_user: Authenticated user.
        
    Returns:
        List of AI suggestions.
    """
    # Verify session exists
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    query = (
        select(AiSuggestion)
        .where(AiSuggestion.session_id == session_id)
        .order_by(AiSuggestion.created_at.desc())
    )
    result = await db.execute(query)
    suggestions = result.scalars().all()

    return [AiSuggestionResponse.model_validate(s) for s in suggestions]
