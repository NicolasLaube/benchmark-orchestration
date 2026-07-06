import httpx


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_sec: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

        response.raise_for_status()
        data = response.json()
        return data.get("response", "")