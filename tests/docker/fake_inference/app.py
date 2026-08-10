from fastapi import FastAPI

app = FastAPI()


@app.get("/health/ready")
async def ready():
    return {"status": "ready"}


@app.post("/infer")
async def infer(payload: dict[str, str]):
    return {
        "answer": "Paris",
        "model": "fake-model",
        "latency_ms": 1,
    }
