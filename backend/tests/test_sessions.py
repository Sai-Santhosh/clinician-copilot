"""Tests for session management."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_header


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, clinician_user, test_patient):
    """Test creating a therapy session."""
    headers = get_auth_header(clinician_user)
    transcript = "Patient presents with anxiety symptoms."
    
    response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": transcript},
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == test_patient.id
    assert data["transcript_length"] == len(transcript)
    assert "transcript" not in data  # Should not expose transcript


@pytest.mark.asyncio
async def test_create_session_nonexistent_patient(client: AsyncClient, clinician_user):
    """Test creating session for nonexistent patient."""
    headers = get_auth_header(clinician_user)
    
    response = await client.post(
        "/api/v1/sessions/patients/9999/sessions",
        headers=headers,
        json={"transcript": "Some content"},
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_patient_sessions(client: AsyncClient, clinician_user, test_patient):
    """Test listing sessions for a patient."""
    headers = get_auth_header(clinician_user)
    
    # Create two sessions
    await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": "First session transcript."},
    )
    await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": "Second session transcript."},
    )
    
    # List sessions
    response = await client.get(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["sessions"]) == 2


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient, clinician_user, test_patient):
    """Test getting a specific session."""
    headers = get_auth_header(clinician_user)
    
    # Create session
    create_response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": "Test transcript content."},
    )
    session_id = create_response.json()["id"]
    
    # Get session
    response = await client.get(
        f"/api/v1/sessions/{session_id}",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["patient_id"] == test_patient.id


@pytest.mark.asyncio
async def test_get_session_transcript(client: AsyncClient, clinician_user, test_patient):
    """Test getting decrypted transcript."""
    headers = get_auth_header(clinician_user)
    transcript = "This is the session transcript content."
    
    # Create session
    create_response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": transcript},
    )
    session_id = create_response.json()["id"]
    
    # Get transcript
    response = await client.get(
        f"/api/v1/sessions/{session_id}/transcript",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == transcript


@pytest.mark.asyncio
async def test_viewer_cannot_get_transcript(client: AsyncClient, viewer_user, clinician_user, test_patient):
    """Test that viewer cannot access transcript."""
    clinician_headers = get_auth_header(clinician_user)
    viewer_headers = get_auth_header(viewer_user)
    
    # Create session as clinician
    create_response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=clinician_headers,
        json={"transcript": "Sensitive content"},
    )
    session_id = create_response.json()["id"]
    
    # Try to get transcript as viewer
    response = await client.get(
        f"/api/v1/sessions/{session_id}/transcript",
        headers=viewer_headers,
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_session(client: AsyncClient, viewer_user, test_patient):
    """Test that viewer cannot create sessions."""
    headers = get_auth_header(viewer_user)
    
    response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": "Some content"},
    )
    
    assert response.status_code == 403
