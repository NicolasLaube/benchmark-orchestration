.PHONY: install pull-model serve benchmark smoke test lint format clean

install:
	uv sync

pull-model:
	ollama pull qwen2.5:0.5b

serve:
	uv run inference-service --model qwen2.5:0.5b --rpm 60 --max-concurrency 4 --port 8000

benchmark:
	uv run orchestrator --queue data/queue_test.jsonl --endpoint http://localhost:8000/infer --out results/run.json

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -f results/*.json results/*.jsonl results/*.csv