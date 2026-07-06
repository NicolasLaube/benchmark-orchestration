# benchmark-orchestration
A system that consumes a queue of benchmark jobs, dispatches their queries against the inference service, collects responses, and produces a results report and a thin HTTP wrapper around a local Ollama model (qwen2.5:0.5b or similar) that enforces the constraints below and behaves like a production inference endpoint would under load.
