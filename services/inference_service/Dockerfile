FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src ./src

RUN uv sync --no-dev --no-cache

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT [ "inference-service" ]
CMD ["--rpm", "60", "--max-concurrency", "8"]