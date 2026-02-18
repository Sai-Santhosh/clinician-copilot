"""Tests for encryption functionality."""

import pytest
from sqlalchemy import select

from app.core.security import encrypt_data, decrypt_data, hash_for_audit
from app.db.models import Session, Patient
from tests.conftest import get_auth_header


def test_encrypt_decrypt_roundtrip():
    """Test that encryption and decryption work correctly."""
    original = "This is sensitive patient data that should be encrypted."
    
    encrypted = encrypt_data(original)
    decrypted = decrypt_data(encrypted)
    
    assert decrypted == original
    assert encrypted != original.encode()


def test_encrypted_data_is_different():
    """Test that encrypted data differs from plaintext."""
    plaintext = "Patient transcript content"
    
    encrypted = encrypt_data(plaintext)
    
    # Encrypted should not contain plaintext
    assert plaintext.encode() not in encrypted
    assert plaintext not in encrypted.decode("latin-1")


def test_hash_for_audit():
    """Test that audit hashing produces consistent hashes."""
    data = "Some data to hash"
    
    hash1 = hash_for_audit(data)
    hash2 = hash_for_audit(data)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length


def test_different_data_different_hash():
    """Test that different data produces different hashes."""
    data1 = "Data version 1"
    data2 = "Data version 2"
    
    hash1 = hash_for_audit(data1)
    hash2 = hash_for_audit(data2)
    
    assert hash1 != hash2


@pytest.mark.asyncio
async def test_transcript_stored_encrypted(client, clinician_user, test_patient, db_session):
    """Test that transcript is stored encrypted in database."""
    headers = get_auth_header(clinician_user)
    transcript_text = "Patient reports feeling anxious and having trouble sleeping."
    
    # Create session
    response = await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": transcript_text},
    )
    
    assert response.status_code == 201
    session_id = response.json()["id"]
    
    # Verify in database - transcript should be encrypted
    result = await db_session.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one()
    
    # The raw bytes should not contain the plaintext
    assert transcript_text.encode() not in session.transcript_encrypted
    
    # But decryption should return original
    decrypted = decrypt_data(session.transcript_encrypted)
    assert decrypted == transcript_text


@pytest.mark.asyncio
async def test_transcript_not_in_response(client, clinician_user, test_patient):
    """Test that transcript is not exposed in session list response."""
    headers = get_auth_header(clinician_user)
    transcript_text = "Sensitive session content here."
    
    # Create session
    await client.post(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
        json={"transcript": transcript_text},
    )
    
    # List sessions - should not contain transcript
    response = await client.get(
        f"/api/v1/sessions/patients/{test_patient.id}/sessions",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that transcript is not in response
    response_text = str(data)
    assert transcript_text not in response_text
    assert "transcript_length" in str(data["sessions"][0])
