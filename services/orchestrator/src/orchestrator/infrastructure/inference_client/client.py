"""
This module contains the InferenceClient class, which is responsible for sending inference requests
to the inference service and handling the responses.
"""

from typing import Self

import httpx
from orchestrator.infrastructure.inference_client.exceptions import (
    InferenceClientError,
    InferenceHttpError,
    InferenceNetworkError,
    InferenceRateLimitedError,
)
from orchestrator.infrastructure.inference_client.models import InferenceResult


class InferenceClient:
    def __init__(
        self,
        endpoint: str,
        timeout_sec: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec
        self._client = client

    async def __aenter__(self) -> Self:
        """
        Enter the asynchronous context manager.

        Returns:
            InferenceClient: The instance of the InferenceClient.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_sec)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """
        Exit the asynchronous context manager.

        Args:
            exc_type: The exception type.
            exc: The exception instance.
            tb: The traceback.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def infer(self, question: str) -> InferenceResult:
        """
        Main method to send an inference request to the inference service.

        Args:
            question (str): The question to be sent for inference.

        Returns:
            InferenceResult: The result of the inference, including the answer, model, and latency.

        Raises:
            InferenceClientError: If the inference request fails or the response is malformed.
        """
        if self._client is None:
            raise RuntimeError(
                "InferenceClient must be used as an async context manager"
            )

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
            # The inference service is supposed to have a Retry-After header in the response
            #  when it returns HTTP 429.
            retry_after_raw = response.headers.get("Retry-After", "1")

            try:
                response_json = response.json()
            except ValueError:
                response_json = {}

            # As explained in Readme, the inference service may return a JSON body with a "detail"
            # field that contains a reason for the rate limit. This is optional, so we parse
            #  it if present.
            reason = _parse_rate_limit_reason(response_json)

            retry_after_sec = _parse_retry_after(retry_after_raw)

            raise InferenceRateLimitedError(
                retry_after_sec=retry_after_sec,
                message=(
                    "Inference service rate-limited the request "
                    f"with Retry-After={retry_after_sec}s"
                ),
                reason=reason,
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


def _parse_retry_after(value: str | None) -> int:
    if value is None:
        return 1

    try:
        return max(1, int(float(value)))
    except ValueError:
        return 1


def _parse_rate_limit_reason(response_json: dict) -> str | None:
    detail = response_json.get("detail")

    if isinstance(detail, dict):
        error = detail.get("error") or detail.get("reason")
        return str(error) if error is not None else None

    if isinstance(detail, str):
        return detail

    return None
