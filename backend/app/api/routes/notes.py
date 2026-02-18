"""Note version management routes."""

from typing import List

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.api.deps import DbSession, ClinicianOrAdmin, AnyAuthUser
from app.db.models import Session, NoteVersion
from app.schemas.notes import (
    NoteVersionResponse,
    NoteVersionUpdate,
    NoteVersionListResponse,
    RollbackRequest,
)
from app.services.notes import NotesService
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter()


@router.get(
    "/sessions/{session_id}/versions",
    response_model=NoteVersionListResponse,
    summary="List note versions",
    description="Get all note versions for a session.",
)
async def list_versions(
    session_id: int,
    db: DbSession,
    current_user: AnyAuthUser,
) -> NoteVersionListResponse:
    """List all versions for a session.
    
    Args:
        session_id: Session ID.
        db: Database session.
        current_user: Authenticated user.
        
    Returns:
        List of note versions.
    """
    # Verify session exists
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    query = (
        select(NoteVersion)
        .where(NoteVersion.session_id == session_id)
        .order_by(NoteVersion.version_number.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()

    return NoteVersionListResponse(
        versions=[NoteVersionResponse.model_validate(v) for v in versions],
        total=len(versions),
    )


@router.get(
    "/versions/{version_id}",
    response_model=NoteVersionResponse,
    summary="Get note version",
    description="Get a specific note version by ID.",
)
async def get_version(
    version_id: int,
    db: DbSession,
    current_user: AnyAuthUser,
) -> NoteVersionResponse:
    """Get a note version by ID.
    
    Args:
        version_id: Version ID.
        db: Database session.
        current_user: Authenticated user.
        
    Returns:
        Note version details.
    """
    version = await db.get(NoteVersion, version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_id} not found",
        )

    return NoteVersionResponse.model_validate(version)


@router.put(
    "/versions/{version_id}",
    response_model=NoteVersionResponse,
    summary="Update note version",
    description="Update a draft note version. Cannot update finalized versions.",
)
async def update_version(
    version_id: int,
    update_data: NoteVersionUpdate,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> NoteVersionResponse:
    """Update a draft note version.
    
    Args:
        version_id: Version ID.
        update_data: Update data.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Updated note version.
    """
    notes_service = NotesService(db)

    try:
        version = await notes_service.update_version(
            version_id=version_id,
            user_id=current_user.id,
            soap_json=update_data.soap_json,
            dx_json=update_data.dx_json,
            meds_json=update_data.meds_json,
            safety_json=update_data.safety_json,
        )
        return NoteVersionResponse.model_validate(version)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/versions/{version_id}/finalize",
    response_model=NoteVersionResponse,
    summary="Finalize note version",
    description="Mark a draft version as final. This action is recorded in audit log.",
)
async def finalize_version(
    version_id: int,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> NoteVersionResponse:
    """Finalize a draft note version.
    
    Args:
        version_id: Version ID.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        Finalized note version.
    """
    notes_service = NotesService(db)

    try:
        version = await notes_service.finalize_version(
            version_id=version_id,
            user_id=current_user.id,
        )
        return NoteVersionResponse.model_validate(version)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/sessions/{session_id}/rollback",
    response_model=NoteVersionResponse,
    summary="Rollback to previous version",
    description="Create a new draft version from a previous version's content.",
)
async def rollback_version(
    session_id: int,
    request: RollbackRequest,
    db: DbSession,
    current_user: ClinicianOrAdmin,
) -> NoteVersionResponse:
    """Rollback to a previous version.
    
    Args:
        session_id: Session ID.
        request: Rollback request with target version.
        db: Database session.
        current_user: Authenticated clinician or admin.
        
    Returns:
        New note version created from rollback.
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
        version = await notes_service.rollback_to_version(
            session_id=session_id,
            target_version_id=request.target_version_id,
            user_id=current_user.id,
        )
        return NoteVersionResponse.model_validate(version)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
