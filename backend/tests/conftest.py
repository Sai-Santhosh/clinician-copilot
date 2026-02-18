"""Test fixtures and configuration."""

import asyncio
import os
from typing import AsyncGenerator, Generator

# Set environment variables BEFORE importing app modules
from cryptography.fernet import Fernet

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_clinician_copilot.db"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32-chars"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["GEMINI_API_KEY"] = ""  # Empty for testing

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_password_hash, create_access_token
from app.db.models import Base, User, Patient, UserRole
from app.db.session import get_db
from app.main import app


# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_async_session() as session:
        yield session
        await session.rollback()

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden dependencies."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("admin123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def clinician_user(db_session: AsyncSession) -> User:
    """Create a clinician user."""
    user = User(
        email="clinician@test.com",
        password_hash=get_password_hash("clinician123!"),
        role=UserRole.CLINICIAN.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer user."""
    user = User(
        email="viewer@test.com",
        password_hash=get_password_hash("viewer123!"),
        role=UserRole.VIEWER.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_patient(db_session: AsyncSession) -> Patient:
    """Create a test patient."""
    patient = Patient(
        name="Test Patient",
        external_id="EXT001",
        dob="1990-01-15",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


def get_auth_header(user: User) -> dict[str, str]:
    """Generate authorization header for a user."""
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_header(admin_user: User) -> dict[str, str]:
    """Get auth header for admin user."""
    return get_auth_header(admin_user)


@pytest.fixture
def clinician_auth_header(clinician_user: User) -> dict[str, str]:
    """Get auth header for clinician user."""
    return get_auth_header(clinician_user)


@pytest.fixture
def viewer_auth_header(viewer_user: User) -> dict[str, str]:
    """Get auth header for viewer user."""
    return get_auth_header(viewer_user)
