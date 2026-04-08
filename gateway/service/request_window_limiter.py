"""
file: gateway/service/request_window_limiter.py

A class that supports sliding window style request rate limiting
"""

import asyncio
import time
from collections import deque
from typing import Deque


class RequestWindowLimiter:
    """
    Async request-window limiter for provider calls.

    This limiter enforces:
        max_requests per window_seconds
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        """
        Initialize the request-window limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window.
            window_seconds: Rolling window size in seconds.
        """

        # 1) Save limiter configuration.
        self._max_requests = max_requests
        self._window_seconds = window_seconds

        # 2) Initialize timestamp storage and synchronization lock.
        self._timestamps: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission for one provider request.

        This method waits until the rolling window has available capacity.
        """

        while True:
            # 1) Attempt to reserve a slot under lock.
            async with self._lock:
                now = time.monotonic()

                # 2) Drop expired timestamps from the rolling window.
                while self._timestamps and (now - self._timestamps[0]) >= self._window_seconds:
                    self._timestamps.popleft()

                # 3) Reserve immediately if capacity exists.
                if len(self._timestamps) < self._max_requests:
                    self._timestamps.append(now)
                    return

                # 4) Compute sleep time until the earliest slot expires.
                sleep_seconds = self._window_seconds - (now - self._timestamps[0])

            # 5) Sleep outside the lock before retrying.
            await asyncio.sleep(max(0.001, sleep_seconds))
