"""API dependencies for authentication and authorization."""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.rate_limiter import get_rate_limiter, InMemoryRateLimiter
from app.db.session import get_db
from app.db.models import User, UserRole

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token credentials.
        db: Database session.
        
    Returns:
        Authenticated User.
        
    Raises:
        HTTPException: If token is invalid or user not found.
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify user is active.
    
    Args:
        current_user: Current user from token.
        
    Returns:
        Active User.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return current_user


def require_role(*roles: str):
    """Create a dependency that requires specific roles.
    
    Args:
        *roles: Allowed roles.
        
    Returns:
        Dependency function.
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
            )
        return current_user

    return role_checker


# Role-based dependencies
require_admin = require_role(UserRole.ADMIN.value)
require_clinician_or_admin = require_role(UserRole.ADMIN.value, UserRole.CLINICIAN.value)
require_any_role = require_role(
    UserRole.ADMIN.value, UserRole.CLINICIAN.value, UserRole.VIEWER.value
)


async def check_rate_limit(
    current_user: Annotated[User, Depends(get_current_active_user)],
    rate_limiter: Annotated[InMemoryRateLimiter, Depends(get_rate_limiter)],
) -> User:
    """Check rate limit for the current user.
    
    Args:
        current_user: Current authenticated user.
        rate_limiter: Rate limiter instance.
        
    Returns:
        User if rate limit not exceeded.
        
    Raises:
        HTTPException: If rate limit exceeded.
    """
    key = f"user:{current_user.id}"
    if not rate_limiter.is_allowed(key):
        remaining = rate_limiter.get_remaining(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"X-RateLimit-Remaining": str(remaining)},
        )
    return current_user


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
ClinicianOrAdmin = Annotated[User, Depends(require_clinician_or_admin)]
AnyAuthUser = Annotated[User, Depends(require_any_role)]
RateLimitedUser = Annotated[User, Depends(check_rate_limit)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
