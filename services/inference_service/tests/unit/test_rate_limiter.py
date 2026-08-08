from inference_service.limiters.limiter_rpm import RpmLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


async def test_rpm_limiter_accepts_requests_below_limit() -> None:
    clock = FakeClock()
    limiter = RpmLimiter(
        rpm=3,
        clock=clock,
    )

    assert await limiter.allow() == (True, 0), "First request should be allowed"
    assert await limiter.allow() == (True, 0), "Second request should be allowed"
    assert await limiter.allow() == (True, 0), "Third request should be allowed"


async def test_rpm_limiter_rejects_request_above_limit() -> None:
    clock = FakeClock()
    limiter = RpmLimiter(
        rpm=2,
        clock=clock,
    )

    allowed, _ = await limiter.allow()
    assert allowed is True, "First request should be allowed"

    allowed, _ = await limiter.allow()
    assert allowed is True, "Second request should be allowed"

    allowed, retry_after = await limiter.allow()

    assert allowed is False, "Request should be rejected when limit is reached"
    assert retry_after > 0, "Retry after should be greater than 0 when request is rejected"


async def test_rpm_limiter_allows_request_after_window_expires() -> None:
    clock = FakeClock()
    limiter = RpmLimiter(
        rpm=1,
        clock=clock,
    )

    allowed, _ = await limiter.allow()
    assert allowed is True, "First request should be allowed"

    allowed, _ = await limiter.allow()
    assert allowed is False, "Request should be rejected when limit is reached"

    clock.advance(60.1)

    allowed, retry_after = await limiter.allow()

    assert allowed is True, "Request should be allowed after the window expires"
    assert retry_after == 0, "Retry after should be 0 after the window expires"
