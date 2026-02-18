"""Audit log routes."""

from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import DbSession, AdminUser
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit import AuditService

router = APIRouter()


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="Get audit logs with optional filters. Admin only.",
)
async def list_audit_logs(
    db: DbSession,
    current_user: AdminUser,
    actor_user_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    limit: int = Query(100, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
) -> AuditLogListResponse:
    """List audit logs with filters.
    
    Args:
        db: Database session.
        current_user: Authenticated admin.
        actor_user_id: Filter by actor.
        entity_type: Filter by entity type.
        entity_id: Filter by entity ID.
        action: Filter by action.
        limit: Maximum results.
        offset: Results offset.
        
    Returns:
        List of audit logs.
    """
    audit_service = AuditService(db)

    logs = await audit_service.get_logs(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
        offset=offset,
    )

    total = await audit_service.count_logs(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
    )


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogResponse,
    summary="Get audit log by ID",
    description="Get a specific audit log entry. Admin only.",
)
async def get_audit_log(
    log_id: int,
    db: DbSession,
    current_user: AdminUser,
) -> AuditLogResponse:
    """Get an audit log entry by ID.
    
    Args:
        log_id: Audit log ID.
        db: Database session.
        current_user: Authenticated admin.
        
    Returns:
        Audit log entry.
    """
    from app.db.models import AuditLog
    from fastapi import HTTPException, status

    log = await db.get(AuditLog, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {log_id} not found",
        )

    return AuditLogResponse.model_validate(log)
