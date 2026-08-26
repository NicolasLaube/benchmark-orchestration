.DEFAULT_GOAL := help

.PHONY: help setup install pull-model serve benchmark smoke \
        test test-cov lint lint-fix format format-check check clean

# ---------------------------------------------------------------------------
# Ensuring that Ollama is installed and available
# ---------------------------------------------------------------------------
OLLAMA_URL ?= http://127.0.0.1:11434


ensure-ollama:
	@if curl -fsS "$(OLLAMA_URL)/api/tags" > /dev/null 2>&1; then \
		echo "Ollama is already running"; \
	else \
		echo "Starting Ollama..."; \
		ollama serve > /tmp/benchmark-orchestrator-ollama.log 2>&1 & \
		for i in $$(seq 1 30); do \
			if curl -fsS "$(OLLAMA_URL)/api/tags" > /dev/null 2>&1; then \
				echo "Ollama is ready"; \
				break; \
			fi; \
			sleep 1; \
		done; \
		curl -fsS "$(OLLAMA_URL)/api/tags" > /dev/null || \
			(echo "Ollama failed to start" && exit 1); \
	fi

ensure-model: ensure-ollama
	@if ollama list | awk 'NR > 1 {print $$1}' | grep -qx "$(MODEL)"; then \
		echo "Model $(MODEL) is already available"; \
	else \
		echo "Pulling model $(MODEL)..."; \
		ollama pull "$(MODEL)"; \
	fi

# ---------------------------------------------------------------------------
# Inference service configuration
# ---------------------------------------------------------------------------

MODEL ?= qwen2.5:0.5b
RPM ?= 60
CONCURRENCY_LIMIT ?= 4
HOST ?= 0.0.0.0
PORT ?= 8000
LIMIT_REASONS_FLAG ?= --expose-limit-reasons

# ---------------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------------

BASE_URL ?= http://localhost:$(PORT)
INFERENCE_ENDPOINT ?= $(BASE_URL)/infer
QUEUE ?= data/queue_smoke.jsonl
RESULTS_DIR ?= results
OUT ?= $(RESULTS_DIR)/run.json
MAX_TARGET_CONCURRENCY ?= 32
SCHEDULER ?= aimd
LOG_LEVEL ?= INFO
MAX_CONCURRENCY ?= 8
TIMEOUT_SEC ?= 120
MAX_RETRIES ?= 3


# Additional arguments can be passed from the command line:
# make test PYTEST_ARGS="-x -s"
# make benchmark ORCHESTRATOR_ARGS="--scheduler aimd"
ORCHESTRATOR_ARGS ?=

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

help:
	@echo "Benchmark Orchestrator"
	@echo ""
	@echo "Setup:"
	@echo "  make install                 Install Python dependencies"
	@echo "  make pull-model              Pull the configured Ollama model"
	@echo "  make setup                   Install dependencies and pull the model"
	@echo ""
	@echo "Run:"
	@echo "  make serve                   Start the inference service"
	@echo "  make benchmark               Run the benchmark orchestrator"
	@echo "  make smoke                   Check /health and /infer"
	@echo ""
	@echo "Quality:"
	@echo "  make test                    Run tests"
	@echo "  make test-cov                Run tests with coverage"
	@echo "  make lint                    Run Ruff checks"
	@echo "  make lint-fix                Fix Ruff violations when possible"
	@echo "  make format                  Format the code"
	@echo "  make format-check            Check formatting without modifying files"
	@echo "  make check                   Run lint, format check, and tests"
	@echo "  make clean                   Remove generated result files"
	@echo ""
	@echo "Examples:"
	@echo "  make serve RPM=120 MAX_CONCURRENCY=8"
	@echo "  make serve MODEL=qwen2.5:1.5b PORT=8080"
	@echo "  make benchmark QUEUE=data/custom.jsonl OUT=results/custom.json"
	@echo "  make test PYTEST_ARGS='-x -s'"

setup: install pull-model

install:
	uv sync

pull-model:
	ollama pull "$(MODEL)"

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

serve: ensure-model
	uv run --package benchmark-inference-service \
		python -m inference_service.api.cli
		--model "$(MODEL)" \
		--rpm "$(RPM)" \
		--max-concurrency "$(CONCURRENCY_LIMIT)" \
		--host "$(HOST)" \
		--port "$(PORT)" \
		$(LIMIT_REASONS_FLAG)

benchmark:
	@mkdir -p "$(RESULTS_DIR)"
	uv run orchestrator \
		--queue "$(QUEUE)" \
		--max-retries "$(MAX_RETRIES)" \
		--scheduler "$(SCHEDULER)" \
		--max-concurrency "$(MAX_CONCURRENCY)" \
		--max-target-concurrency "$(MAX_TARGET_CONCURRENCY)" \
		$(ORCHESTRATOR_ARGS)

smoke:
	@echo "Checking health endpoint..."
	@curl --fail --silent --show-error "$(BASE_URL)/health"
	@echo ""
	@echo "Checking inference endpoint..."
	@curl --fail --silent --show-error \
		-X POST "$(INFERENCE_ENDPOINT)" \
		-H "Content-Type: application/json" \
		-d '{"question":"Reply with exactly: pong"}'
	@echo ""

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------

test:
	uv run pytest -v


lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

format-check:
	uv run ruff format . --check

check: lint format-check test

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean:
	@mkdir -p "$(RESULTS_DIR)"
	rm -f \
		"$(RESULTS_DIR)"/*.json \
		"$(RESULTS_DIR)"/*.jsonl \
		"$(RESULTS_DIR)"/*.csv