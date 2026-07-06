import httpx

from orchestrator.models import InferenceResult


class InferenceClientError(Exception):
    """Base error raised when the orchestrator cannot get a valid inference response."""


class InferenceRateLimitedError(InferenceClientError):
    """Raised when the inference service returns HTTP 429."""

    def __init__(self, retry_after_sec: int, message: str) -> None:
        super().__init__(message)
        self.retry_after_sec = retry_after_sec


class InferenceHttpError(InferenceClientError):
    """Raised when the inference service returns a non-2xx HTTP response."""


class InferenceNetworkError(InferenceClientError):
    """Raised when the inference service cannot be reached or times out."""


class InferenceClient:
    def __init__(
        self,
        endpoint: str,
        timeout_sec: float = 120.0,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "InferenceClient":
        self._client = httpx.AsyncClient(timeout=self.timeout_sec)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def infer(self, question: str) -> InferenceResult:
        if self._client is None:
            raise RuntimeError("InferenceClient must be used as an async context manager")

        try:
            response = await self._client.post(
                self.endpoint,
                json={"question": question},
            )

        except httpx.TimeoutException as exc:
            raise InferenceNetworkError(
                f"Inference request timed out after {self.timeout_sec}s"
            ) from exc

        except httpx.RequestError as exc:
            raise InferenceNetworkError(
                f"Failed to call inference service at {self.endpoint}: {exc}"
            ) from exc

        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After", "1")

            try:
                retry_after_sec = max(1, int(float(retry_after_raw)))
            except ValueError:
                retry_after_sec = 1

            raise InferenceRateLimitedError(
                retry_after_sec=retry_after_sec,
                message=(
                    "Inference service rate-limited the request "
                    f"with Retry-After={retry_after_sec}s"
                ),
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise InferenceHttpError(
                f"Inference service returned HTTP {response.status_code}: {response.text}"
            ) from exc

        data = response.json()

        try:
            return InferenceResult(
                answer=data["answer"],
                model=data["model"],
                latency_ms=int(data["latency_ms"]),
            )
        except KeyError as exc:
            raise InferenceClientError(
                f"Malformed inference response, missing field: {exc}"
            ) from exc
