from typing import Protocol


class AIGenerator(Protocol):
    async def generate(self, prompt: str) -> str: ...

    async def health_check(self) -> bool: ...
