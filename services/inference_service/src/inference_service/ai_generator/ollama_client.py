import httpx
from inference_service.ai_generator.ai_generator import AIGenerator


class OllamaClient(AIGenerator):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_sec: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec
        self.client = httpx.AsyncClient(timeout=self.timeout_sec)

    async def generate(self, prompt: str) -> str:
        """Generates the response from the prompt."""
        response = await self.client.post(
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

    async def close(self):
        """Closes the client."""

        await self.client.aclose()

    async def health_check(self) -> bool:
        """Health route for Ollama client.

        Returns:
            - bool: whether the model is available for the Ollama client.
        """

        response = await self.client.get(f"{self.base_url}/api/tags")

        response.raise_for_status()

        models = response.json().get("models", [])

        return any(self.model == model.get("name") for model in models)
