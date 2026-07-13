from typing import Protocol


class AIGenerator(Protocol):
    async def generate(self, prompt: str) -> str: ...
