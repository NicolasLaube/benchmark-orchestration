import asyncio
import math
import time
from collections import deque


class RpmLimiter:
    def __init__(self, rpm: int) -> None:
        if rpm <= 0:
            raise ValueError("rpm must be greater than 0")

        self.rpm = rpm
        self.timestamps: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def allow(self) -> tuple[bool, int]:
        """
        Returns:
            allowed: whether the request can proceed
            retry_after_sec: number of seconds to wait if rejected
        """
        async with self.lock:
            now = time.monotonic()

            while self.timestamps and self.timestamps[0] <= now - 60:
                self.timestamps.popleft()

            if len(self.timestamps) >= self.rpm:
                oldest = self.timestamps[0]
                retry_after = math.ceil(60 - (now - oldest))
                return False, max(1, retry_after)

            self.timestamps.append(now)
            return True, 0


class ConcurrencyLimiter:
    def __init__(self, max_concurrency: int) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")

        self.max_concurrency = max_concurrency
        self.in_flight = 0
        self.lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self.lock:
            if self.in_flight >= self.max_concurrency:
                return False

            self.in_flight += 1
            return True

    async def release(self) -> None:
        async with self.lock:
            self.in_flight = max(0, self.in_flight - 1)

    async def current_in_flight(self) -> int:
        async with self.lock:
            return self.in_flight
