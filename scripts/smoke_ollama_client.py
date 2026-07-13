import asyncio

from inference_service.ai_generator.ollama_client import OllamaClient


async def main() -> None:
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="qwen2.5:0.5b",
        timeout_sec=120.0,
    )

    answer = await client.generate("What is the capital of France?")

    print("Response from Ollama:", answer)


if __name__ == "__main__":
    asyncio.run(main())
