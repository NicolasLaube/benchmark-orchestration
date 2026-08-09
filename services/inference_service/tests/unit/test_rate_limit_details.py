import pytest
from inference_service.api.routes.inference import rate_limit_detail


@pytest.mark.parametrize(
    ("error", "expose", "expected"),
    [
        (
            "rpm_limited",
            True,
            {"error": "rpm_limited"},
        ),
        (
            "concurrency_limited",
            True,
            {"error": "concurrency_limited"},
        ),
        (
            "rpm_limited",
            False,
            "rate_limited",
        ),
        (
            "concurrency_limited",
            False,
            "rate_limited",
        ),
    ],
)
def test_rate_limit_detail(
    error: str,
    expose: bool,
    expected: dict[str, str] | str,
) -> None:
    assert rate_limit_detail(error, expose) == expected
