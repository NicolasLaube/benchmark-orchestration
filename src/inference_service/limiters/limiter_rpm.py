import asyncio
import math
import time
from collections import deque
from typing import Protocol


class RpmGate(Protocol):
    async def allow(self) -> tuple[bool, int]: ...


class RpmLimiter:
    WINDOW_SECONDS = 60.0

    def __init__(
        self,
        rpm: int,
        clock=time.monotonic,
    ) -> None:
        if rpm <= 0:
            raise ValueError("rpm must be greater than 0")

        self.rpm = rpm
        self.clock = clock
        self.timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def allow(self) -> tuple[bool, int]:
        """
        Check if a request is allowed based on the RPM limit.
        Returns:
            allowed: whether the request can proceed
            retry_after_sec: number of seconds to wait if rejected
        """
        # Acquire the lock to ensure thread safety when checking and updating the timestamps.
        # (Even if here, since there is no await in the critical section, it is still good practice
        # to use a lock to prevent potential race conditions in a multi-threaded environment.)
        # async with garantees that the lock is released even if an exception occurs within the
        # block.
        async with self._lock:
            # Get the current time in seconds since the epoch,
            # 0 corresponds to the Unix epoch (January 1, 1970).
            now = self.clock()

            # update slideing window of timestamps
            while self.timestamps and self.timestamps[0] <= now - self.WINDOW_SECONDS:
                self.timestamps.popleft()

            # check if we are within the RPM limit
            if len(self.timestamps) >= self.rpm:
                oldest = self.timestamps[0]
                # Calculate the time to wait until the oldest timestamp is outside the 60-second
                # window.
                retry_after = math.ceil(self.WINDOW_SECONDS - (now - oldest))
                return False, max(1, retry_after)

            self.timestamps.append(now)
            return True, 0
