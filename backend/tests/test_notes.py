"""Tests for note version management."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import NoteVersion, NoteStatus
from tests.conftest import get_auth_header


@pytest.fixture
async def session_with_version(client, clinician_user, test_patient, db_session):
    """Create a session with a note version."""
    headers = get_auth_header(clinician_user)
    
    # Create session
    session_response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": "Patient reports anxiety symptoms."},
    )
    session_id = session_response.json()["id"]
    
    # Create a draft version manually (normally done via AI generation)
    version = NoteVersion(
        session_id=session_id,
        version_number=1,
        status=NoteStatus.DRAFT.value,
        soap_json='{"subjective": {"content": "Test", "citations": []}}',
        created_by_user_id=clinician_user.id,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)
    
    return {"session_id": session_id, "version_id": version.id}


@pytest.mark.asyncio
async def test_list_versions(client, clinician_user, session_with_version):
    """Test listing note versions."""
    headers = get_auth_header(clinician_user)
    session_id = session_with_version["session_id"]
    
    response = await client.get(
        f"/api/v1/notes/sessions/{session_id}/versions",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["versions"]) == 1


@pytest.mark.asyncio
async def test_get_version(client, clinician_user, session_with_version):
    """Test getting a specific version."""
    headers = get_auth_header(clinician_user)
    version_id = session_with_version["version_id"]
    
    response = await client.get(
        f"/api/v1/notes/versions/{version_id}",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == version_id
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_update_draft_version(client, clinician_user, session_with_version):
    """Test updating a draft version."""
    headers = get_auth_header(clinician_user)
    version_id = session_with_version["version_id"]
    
    new_soap = '{"subjective": {"content": "Updated content", "citations": []}}'
    
    response = await client.put(
        f"/api/v1/notes/versions/{version_id}",
        headers=headers,
        json={"soap_json": new_soap},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["soap_json"] == new_soap


@pytest.mark.asyncio
async def test_finalize_version(client, clinician_user, session_with_version):
    """Test finalizing a draft version."""
    headers = get_auth_header(clinician_user)
    version_id = session_with_version["version_id"]
    
    response = await client.post(
        f"/api/v1/notes/versions/{version_id}/finalize",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "final"


@pytest.mark.asyncio
async def test_cannot_update_finalized_version(client, clinician_user, session_with_version):
    """Test that finalized versions cannot be updated."""
    headers = get_auth_header(clinician_user)
    version_id = session_with_version["version_id"]
    
    # Finalize first
    await client.post(
        f"/api/v1/notes/versions/{version_id}/finalize",
        headers=headers,
    )
    
    # Try to update
    response = await client.put(
        f"/api/v1/notes/versions/{version_id}",
        headers=headers,
        json={"soap_json": '{"new": "content"}'},
    )
    
    assert response.status_code == 400
    assert "finalized" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rollback_version(client, clinician_user, session_with_version, db_session):
    """Test rolling back to a previous version."""
    headers = get_auth_header(clinician_user)
    session_id = session_with_version["session_id"]
    version_id = session_with_version["version_id"]
    
    # Create a second version
    version2 = NoteVersion(
        session_id=session_id,
        version_number=2,
        status=NoteStatus.DRAFT.value,
        soap_json='{"subjective": {"content": "Version 2", "citations": []}}',
        created_by_user_id=clinician_user.id,
    )
    db_session.add(version2)
    await db_session.commit()
    
    # Rollback to version 1
    response = await client.post(
        f"/api/v1/notes/sessions/{session_id}/rollback",
        headers=headers,
        json={"target_version_id": version_id},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 3  # New version created
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_viewer_cannot_update_version(client, viewer_user, session_with_version):
    """Test that viewer cannot update versions."""
    headers = get_auth_header(viewer_user)
    version_id = session_with_version["version_id"]
    
    response = await client.put(
        f"/api/v1/notes/versions/{version_id}",
        headers=headers,
        json={"soap_json": '{"new": "content"}'},
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_finalize(client, viewer_user, session_with_version):
    """Test that viewer cannot finalize versions."""
    headers = get_auth_header(viewer_user)
    version_id = session_with_version["version_id"]
    
    response = await client.post(
        f"/api/v1/notes/versions/{version_id}/finalize",
        headers=headers,
    )
    
    assert response.status_code == 403
