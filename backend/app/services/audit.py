"""Audit service for immutable logging."""

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_for_audit
from app.db.models import AuditLog

logger = get_logger()


class AuditService:
    """Service for managing immutable audit logs."""

    def __init__(self, db: AsyncSession):
        """Initialize audit service.
        
        Args:
            db: Database session.
        """
        self.db = db

    async def log(
        self,
        actor_user_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        before_data: Optional[str] = None,
        after_data: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Create an immutable audit log entry.
        
        Args:
            actor_user_id: User performing the action.
            action: Action type (create, update, delete, finalize, etc.).
            entity_type: Type of entity (session, note_version, patient, etc.).
            entity_id: ID of the entity.
            before_data: JSON string of state before action.
            after_data: JSON string of state after action.
            metadata: Additional metadata dict.
            
        Returns:
            Created AuditLog entry.
        """
        # Hash the data for immutability verification
        before_hash = hash_for_audit(before_data) if before_data else None
        after_hash = hash_for_audit(after_data) if after_data else None

        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_hash=before_hash,
            after_hash=after_hash,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            f"Audit log created: {action} on {entity_type}:{entity_id}",
            extra={
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "actor_user_id": actor_user_id,
            },
        )

        return audit_log

    async def get_logs(
        self,
        actor_user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs with optional filters.
        
        Args:
            actor_user_id: Filter by actor.
            entity_type: Filter by entity type.
            entity_id: Filter by entity ID.
            action: Filter by action.
            limit: Maximum results.
            offset: Results offset.
            
        Returns:
            List of matching audit logs.
        """
        query = select(AuditLog).order_by(AuditLog.created_at.desc())

        if actor_user_id is not None:
            query = query.where(AuditLog.actor_user_id == actor_user_id)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if action is not None:
            query = query.where(AuditLog.action == action)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_logs(
        self,
        actor_user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> int:
        """Count audit logs matching filters.
        
        Args:
            actor_user_id: Filter by actor.
            entity_type: Filter by entity type.
            entity_id: Filter by entity ID.
            action: Filter by action.
            
        Returns:
            Count of matching logs.
        """
        from sqlalchemy import func

        query = select(func.count(AuditLog.id))

        if actor_user_id is not None:
            query = query.where(AuditLog.actor_user_id == actor_user_id)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if action is not None:
            query = query.where(AuditLog.action == action)

        result = await self.db.execute(query)
        return result.scalar() or 0
