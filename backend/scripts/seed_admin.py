#!/usr/bin/env python3
"""Script to seed an admin user."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import async_session
from app.db.models import User, UserRole


async def seed_admin(
    email: str = "admin@clinician-copilot.local",
    password: str = "admin123!",
) -> None:
    """Create an admin user if not exists.
    
    Args:
        email: Admin email address.
        password: Admin password.
    """
    async with async_session() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user '{email}' already exists.")
            return

        # Create admin user
        admin = User(
            email=email,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(admin)
        await db.commit()

        print(f"Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  Role: admin")
        print()
        print("IMPORTANT: Change the password after first login!")


async def seed_demo_users() -> None:
    """Create demo users for testing."""
    users = [
        ("admin@clinician-copilot.local", "admin123!", UserRole.ADMIN.value),
        ("clinician@clinician-copilot.local", "clinician123!", UserRole.CLINICIAN.value),
        ("viewer@clinician-copilot.local", "viewer123!", UserRole.VIEWER.value),
    ]

    async with async_session() as db:
        for email, password, role in users:
            result = await db.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()

            if existing:
                print(f"User '{email}' already exists, skipping.")
                continue

            user = User(
                email=email,
                password_hash=get_password_hash(password),
                role=role,
                is_active=True,
            )
            db.add(user)
            print(f"Created user: {email} ({role})")

        await db.commit()

    print()
    print("Demo users created successfully!")
    print("Passwords are: admin123!, clinician123!, viewer123!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", default="admin@clinician-copilot.local", help="Admin email")
    parser.add_argument("--password", default="admin123!", help="Admin password")
    parser.add_argument("--demo", action="store_true", help="Create demo users (admin, clinician, viewer)")

    args = parser.parse_args()

    if args.demo:
        asyncio.run(seed_demo_users())
    else:
        asyncio.run(seed_admin(args.email, args.password))
