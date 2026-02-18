"""Security utilities: password hashing, JWT, encryption."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()


# Cache the Fernet instance
_fernet_instance: Optional[Fernet] = None


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    global _fernet_instance
    
    if _fernet_instance is not None:
        return _fernet_instance
    
    key = settings.encryption_key
    if not key:
        # Generate a key for development if not set
        key = Fernet.generate_key().decode()
        
    # Ensure the key is valid Fernet format
    try:
        _fernet_instance = Fernet(key.encode())
    except Exception:
        # If key is invalid, generate a new one (development only)
        _fernet_instance = Fernet(Fernet.generate_key())
    
    return _fernet_instance


def encrypt_data(data: str) -> bytes:
    """Encrypt sensitive data using Fernet."""
    fernet = get_fernet()
    return fernet.encrypt(data.encode())


def decrypt_data(encrypted_data: bytes) -> str:
    """Decrypt data using Fernet."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_data).decode()


def hash_for_audit(data: str) -> str:
    """Create a SHA-256 hash for audit logging."""
    return hashlib.sha256(data.encode()).hexdigest()


def generate_transcript_id() -> str:
    """Generate a unique transcript ID for logging (no PHI)."""
    return secrets.token_hex(16)


def hash_transcript_for_log(transcript_id: str, length: int) -> str:
    """Create a safe log representation of a transcript."""
    return f"transcript:{hash_for_audit(transcript_id)[:16]}:len={length}"
