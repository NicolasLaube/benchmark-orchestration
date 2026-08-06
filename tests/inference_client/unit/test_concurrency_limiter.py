import asyncio

from inference_service.limiters.limiter_concurrency import ConcurrencyLimiter


async def test_concurrency_limiter_accepts_up_to_limit() -> None:
    limiter = ConcurrencyLimiter(max_concurrency=2)

    assert await limiter.try_acquire() is True
    assert await limiter.try_acquire() is True
    assert await limiter.try_acquire() is False


async def test_concurrency_limiter_accepts_again_after_release() -> None:
    limiter = ConcurrencyLimiter(max_concurrency=1)

    assert await limiter.try_acquire() is True
    assert await limiter.try_acquire() is False

    await limiter.release()

    assert await limiter.try_acquire() is True


async def test_concurrency_limiter_never_exceeds_capacity() -> None:
    limiter = ConcurrencyLimiter(max_concurrency=3)

    active = 0
    maximum_observed = 0
    state_lock = asyncio.Lock()

    async def worker() -> None:
        nonlocal active, maximum_observed

        acquired = await limiter.try_acquire()

        if not acquired:
            return

        try:
            async with state_lock:
                active += 1
                maximum_observed = max(maximum_observed, active)

            await asyncio.sleep(0)

            async with state_lock:
                active -= 1
        finally:
            await limiter.release()

    await asyncio.gather(*(worker() for _ in range(100)))

    assert maximum_observed <= 3
