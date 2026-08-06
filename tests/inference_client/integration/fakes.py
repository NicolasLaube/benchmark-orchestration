import httpx


class FakeOllamaClient:
    def __init__(self, answer: str = "Paris") -> None:
        self.answer = answer
        self.received_prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.received_prompts.append(prompt)
        return self.answer


class FailingOllamaClient:
    async def generate(self, prompt: str) -> str:
        request = httpx.Request(
            method="POST",
            url="http://ollama:11434/api/generate",
        )

        raise httpx.ConnectError(
            "Connection refused",
            request=request,
        )


class AllowingRpmLimiter:
    async def allow(self) -> tuple[bool, int]:
        return True, 0


class RejectingRpmLimiter:
    def __init__(self, retry_after: int = 42) -> None:
        self.retry_after = retry_after

    async def allow(self) -> tuple[bool, int]:
        return False, self.retry_after


class AllowingConcurrencyLimiter:
    def __init__(self) -> None:
        self.acquire_calls = 0
        self.release_calls = 0

    async def try_acquire(self) -> bool:
        self.acquire_calls += 1
        return True

    async def release(self) -> None:
        self.release_calls += 1


class RejectingConcurrencyLimiter:
    def __init__(self) -> None:
        self.acquire_calls = 0
        self.release_calls = 0

    async def try_acquire(self) -> bool:
        self.acquire_calls += 1
        return False

    async def release(self) -> None:
        self.release_calls += 1
