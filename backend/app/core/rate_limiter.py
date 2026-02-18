"""Simple in-memory rate limiter."""

import time
from collections import defaultdict
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


class InMemoryRateLimiter:
    """Simple sliding window rate limiter using in-memory storage."""

    def __init__(self, requests_per_minute: Optional[int] = None):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per key.
        """
        self.requests_per_minute = requests_per_minute or settings.rate_limit_requests_per_minute
        self.window_size = 60  # 1 minute window
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed for the given key.
        
        Args:
            key: Identifier for the rate limit (e.g., user_id, IP address).
            
        Returns:
            True if request is allowed, False if rate limited.
        """
        current_time = time.time()
        window_start = current_time - self.window_size

        # Clean old requests outside the window
        self._requests[key] = [
            req_time for req_time in self._requests[key] if req_time > window_start
        ]

        # Check if under limit
        if len(self._requests[key]) < self.requests_per_minute:
            self._requests[key].append(current_time)
            return True

        return False

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for the key in the current window.
        
        Args:
            key: Identifier for the rate limit.
            
        Returns:
            Number of remaining requests allowed.
        """
        current_time = time.time()
        window_start = current_time - self.window_size

        # Clean old requests
        self._requests[key] = [
            req_time for req_time in self._requests[key] if req_time > window_start
        ]

        return max(0, self.requests_per_minute - len(self._requests[key]))

    def reset(self, key: str) -> None:
        """Reset the rate limit for a key.
        
        Args:
            key: Identifier to reset.
        """
        if key in self._requests:
            del self._requests[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance."""
    return rate_limiter
