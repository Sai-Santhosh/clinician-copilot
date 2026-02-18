"""Tests for role-based access control."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_admin_can_access_audit_logs(client: AsyncClient, admin_user):
    """Test that admin can access audit logs."""
    headers = get_auth_header(admin_user)
    
    response = await client.get("/api/v1/audit/logs", headers=headers)
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clinician_cannot_access_audit_logs(client: AsyncClient, clinician_user):
    """Test that clinician cannot access audit logs."""
    headers = get_auth_header(clinician_user)
    
    response = await client.get("/api/v1/audit/logs", headers=headers)
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_access_audit_logs(client: AsyncClient, viewer_user):
    """Test that viewer cannot access audit logs."""
    headers = get_auth_header(viewer_user)
    
    response = await client.get("/api/v1/audit/logs", headers=headers)
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_clinician_can_create_patient(client: AsyncClient, clinician_user):
    """Test that clinician can create a patient."""
    headers = get_auth_header(clinician_user)
    
    response = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "New Patient", "dob": "1985-05-20"},
    )
    
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_viewer_cannot_create_patient(client: AsyncClient, viewer_user):
    """Test that viewer cannot create a patient."""
    headers = get_auth_header(viewer_user)
    
    response = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "New Patient", "dob": "1985-05-20"},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_read_patients(client: AsyncClient, viewer_user, test_patient):
    """Test that viewer can read patients."""
    headers = get_auth_header(viewer_user)
    
    response = await client.get("/api/v1/patients", headers=headers)
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_do_everything(client: AsyncClient, admin_user, test_patient):
    """Test that admin has full access."""
    headers = get_auth_header(admin_user)
    
    # Read patients
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    
    # Create patient
    response = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"name": "Admin Patient"},
    )
    assert response.status_code == 201
    
    # Access audit logs
    response = await client.get("/api/v1/audit/logs", headers=headers)
    assert response.status_code == 200
