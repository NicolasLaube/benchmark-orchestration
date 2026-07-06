# Benchmark Orchestrator

A small end-to-end system for running benchmark workloads against a rate-limited local inference endpoint.

The project contains two separate processes:

1. **Inference service**: an HTTP wrapper around a local Ollama model. It enforces configurable RPM and concurrency limits and returns explicit `429` responses with `Retry-After` when limits are reached.
2. **Benchmark orchestrator**: an adaptive runner that consumes benchmark jobs, sends questions to the inference service, handles backpressure, retries safely, grades responses, displays live progress, and writes a structured results report.

---

## Quickstart

### 1. Install dependencies

```bash
uv sync
```

### 2. Pull the Ollama model

```bash
ollama pull qwen2.5:0.5b
```

### 3. Start the inference service

```bash
make serve
```

Equivalent command:

```bash
uv run inference-service --model qwen2.5:0.5b --rpm 60 --max-concurrency 4 --port 8000
```

### 4. Run the benchmark orchestrator

In another terminal:

```bash
make benchmark
```

Equivalent command:

```bash
uv run benchmark-orchestrator \
  --queue data/queue.jsonl \
  --endpoint http://localhost:8000/infer \
  --out results/run.json
```

---

## Input files

### `benchmark.csv`

A CSV file containing simple question-answer pairs:

```csv
id,question,expected_answer
1,What is the capital of France?,Paris
2,What is 12 times 8?,96
```

### `queue.jsonl`

A JSONL file where each line describes one benchmark run:

```json
{"benchmark_id": "run_001", "csv_path": "data/benchmark.csv"}
{"benchmark_id": "run_002", "csv_path": "data/benchmark.csv"}
```

The sample queue references the same benchmark multiple times to produce a larger workload.

---

## Output

The orchestrator writes a structured JSON results file containing:

* total wall time
* per-benchmark wall time
* total requests
* failure count
* retry count
* HTTP 429 count
* throughput in requests per second
* p50 and p95 request latency
* overall accuracy

Example:

```json
{
  "total_wall_time_sec": 842.5,
  "total_requests": 1000,
  "successful_requests": 998,
  "failure_count": 2,
  "retry_count": 37,
  "http_429_count": 21,
  "throughput_req_s": 1.18,
  "latency_ms": {
    "p50": 812,
    "p95": 2310
  },
  "accuracy": 0.91
}
```

---

## Design

```text
queue.jsonl
    |
    v
Benchmark Orchestrator
    |
    | HTTP POST /infer
    v
Rate-limited Inference Service
    |
    | local call
    v
Ollama model
```

The inference service intentionally behaves like a constrained production endpoint. It accepts requests only when both limits allow it:

* maximum requests per minute
* maximum concurrent in-flight requests

If either limit is reached, the service returns:

```http
429 Too Many Requests
Retry-After: <seconds>
```

The service does not silently drop requests and does not queue them internally. Saturation is exposed explicitly to the caller.

The orchestrator owns the workload queue. It decides when to send requests, how many to keep in flight, when to retry, and how to adapt its sending rate.

---

## Adaptive scheduling

The orchestrator does not assume the service limits upfront.

Instead, it uses feedback from the inference service:

* successful requests indicate available capacity;
* `429` responses indicate backpressure;
* `Retry-After` tells the orchestrator when it is safe to retry;
* timeouts and server errors are retried with bounded exponential backoff.

The scheduler uses a conservative adaptive strategy:

* gradually increase target throughput while requests succeed;
* reduce target throughput and concurrency when `429` responses appear;
* requeue rate-limited requests instead of counting them as final failures;
* keep final failures only for requests that exceed the retry budget.

This allows the orchestrator to adjust when the service RPM or concurrency limits are changed.

---

## Observability

While running, the orchestrator displays live execution state in the terminal:

* completed requests
* in-flight requests
* current throughput
* target throughput
* retry count
* HTTP 429 count
* failure count
* accuracy
* latency percentiles
* ETA

The goal is to make the run understandable while it is happening, not only after the final report is written.

---

## Grading

Answer grading is intentionally simple.

A response is marked correct when the expected answer appears as a case-insensitive substring of the model output.

This keeps the focus on orchestration, backpressure, and reliability rather than NLP evaluation quality.

---

## Tradeoffs

This implementation favors a working, observable end-to-end system over a heavier distributed architecture.

Current tradeoffs:

* in-memory queue only;
* no persistent checkpoint/resume mechanism;
* simple substring-based grading;
* no distributed workers;
* no authentication;
* no Prometheus/Grafana integration;
* Docker is not the default execution path to keep local Ollama setup simple.

---

## What I would build next

With more time, I would add:

* checkpointing and resume for long benchmark runs;
* priority queues for mixed workloads;
* richer benchmark job types;
* Prometheus metrics and structured logs;
* distributed workers with shared state;
* more advanced adaptive rate control;
* optional Docker Compose setup for reproducible deployment.

---

## AI usage

AI tooling was used to accelerate boilerplate generation, review edge cases in the adaptive rate limiter, and refine the README structure.

The system design, tradeoff decisions, load-testing behavior, and final implementation were manually reviewed and tested end-to-end.

