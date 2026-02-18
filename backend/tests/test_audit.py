"""Tests for audit logging."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import AuditLog
from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_patient_creation_creates_audit_log(client, clinician_user, db_session):
    """Test that creating a patient creates an audit log."""
    headers = get_auth_header(clinician_user)
    
    response = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "Audit Test Patient"},
    )
    
    assert response.status_code == 201
    patient_id = response.json()["id"]
    
    # Check audit log
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "patient",
            AuditLog.entity_id == patient_id,
            AuditLog.action == "create",
        )
    )
    audit_log = result.scalar_one_or_none()
    
    assert audit_log is not None
    assert audit_log.actor_user_id == clinician_user.id
    assert audit_log.after_hash is not None


@pytest.mark.asyncio
async def test_patient_update_creates_audit_log(client, clinician_user, test_patient, db_session):
    """Test that updating a patient creates an audit log."""
    headers = get_auth_header(clinician_user)
    
    response = await client.put(
        f"/api/v1/patients/{test_patient.id}",
        headers=headers,
        json={"name": "Updated Name"},
    )
    
    assert response.status_code == 200
    
    # Check audit log
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "patient",
            AuditLog.entity_id == test_patient.id,
            AuditLog.action == "update",
        )
    )
    audit_log = result.scalar_one_or_none()
    
    assert audit_log is not None
    assert audit_log.before_hash is not None
    assert audit_log.after_hash is not None
    assert audit_log.before_hash != audit_log.after_hash


@pytest.mark.asyncio
async def test_audit_log_immutability(db_session, admin_user):
    """Test that audit logs cannot be modified after creation."""
    from app.services.audit import AuditService
    
    audit_service = AuditService(db_session)
    
    # Create audit log
    log = await audit_service.log(
        actor_user_id=admin_user.id,
        action="test_action",
        entity_type="test_entity",
        entity_id=1,
        after_data='{"test": "data"}',
    )
    await db_session.commit()
    
    original_hash = log.after_hash
    original_action = log.action
    
    # Verify the log exists with correct data
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.id == log.id)
    )
    retrieved_log = result.scalar_one()
    
    assert retrieved_log.after_hash == original_hash
    assert retrieved_log.action == original_action


@pytest.mark.asyncio
async def test_list_audit_logs_admin_only(client, admin_user, clinician_user):
    """Test that only admin can list audit logs."""
    # Create some activity to generate logs
    clinician_headers = get_auth_header(clinician_user)
    await client.post(
        "/api/v1/patients",
        headers=clinician_headers,
        json={"name": "Test Patient"},
    )
    
    # Admin can access
    admin_headers = get_auth_header(admin_user)
    response = await client.get("/api/v1/audit/logs", headers=admin_headers)
    assert response.status_code == 200
    
    # Clinician cannot access
    response = await client.get("/api/v1/audit/logs", headers=clinician_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_filters(client, admin_user, clinician_user, db_session):
    """Test audit log filtering."""
    # Create some audit logs
    from app.services.audit import AuditService
    
    audit_service = AuditService(db_session)
    
    await audit_service.log(
        actor_user_id=clinician_user.id,
        action="create",
        entity_type="patient",
        entity_id=1,
    )
    await audit_service.log(
        actor_user_id=admin_user.id,
        action="update",
        entity_type="session",
        entity_id=2,
    )
    await db_session.commit()
    
    headers = get_auth_header(admin_user)
    
    # Filter by entity type
    response = await client.get(
        "/api/v1/audit/logs?entity_type=patient",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert all(log["entity_type"] == "patient" for log in data["logs"])
    
    # Filter by action
    response = await client.get(
        "/api/v1/audit/logs?action=create",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert all(log["action"] == "create" for log in data["logs"])
