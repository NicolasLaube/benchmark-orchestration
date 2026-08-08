import asyncio
from typing import Protocol


class ConcurrencyGate(Protocol):
    async def try_acquire(self) -> bool: ...

    async def release(self) -> None: ...


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
            if self.in_flight <= 0:
                raise RuntimeError("Concurrency limiter released without acquisition")

            self.in_flight -= 1

    async def current_in_flight(self) -> int:
        async with self.lock:
            return self.in_flight
