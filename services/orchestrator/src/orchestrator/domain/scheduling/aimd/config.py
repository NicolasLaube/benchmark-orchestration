from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdaptiveAimdSchedulerConfig:
    """Behavioral configuration for the adaptive scheduler.

    Dependencies and observability adapters are injected separately in the
    scheduler constructor.
    """

    # The initial concurrency level to start the scheduler with.
    initial_concurrency: int = 1
    # The maximum target concurrency level that the scheduler can reach.
    # Why? Because we want to avoid unbounded concurrency growth in case of misbehaving servers or
    # misconfigured benchmarks. This acts as a safety ceiling for the adaptive scheduler.
    max_target_concurrency: int = 32

    # The initial launch interval in seconds to start the scheduler with.
    initial_launch_interval_sec: float = 0.10
    min_launch_interval_sec: float = 0.0
    max_launch_interval_sec: float = 10.0

    # The maximum number of retries for a failed request before giving up.
    max_retries: int = 3
    # The maximum backoff time in seconds for retrying failed requests.
    max_backoff_sec: float = 8.0

    # The number of consecutive successful requests required to consider the scheduler's
    # current concurrency level as stable and to potentially increase it.
    successes_before_concurrency_increase: int = 5

    # The factor by which the launch interval is decreased during a probe phase.
    probe_speedup_factor: float = 0.80

    # The factor by which the launch interval is decreased after a successful request in the
    # adaptive phase.
    # Why is it smaller? Because we want to be more conservative in the adaptive phase, as we have
    # already observed some successful requests and want to avoid overshooting the optimal launch
    # interval.
    success_speedup_factor: float = 0.90

    # The factor by which the launch interval is decreased when the scheduler is in a generic
    # overload
    # state (i.e., not specifically limited by RPM or concurrency). This factor is used to adjust
    # the launch interval in response to observed overload conditions, helping to prevent further
    # overload and maintain a stable request flow.
    generic_overload_concurrency_factor: float = 0.70

    # The number of consecutive successful requests required to consider the scheduler's
    # current concurrency level as stable and to potentially increase it.
    successes_before_rpm_probe: int = 5
    # The target utilization of the request rate per minute (RPM) relative to the estimated RPM
    # limit. This value should be between 0 and 1, where 1 means the scheduler will try to reach
    # the estimated RPM limit, and values less than 1 will aim for a lower RPM to avoid hitting the
    # limit. This helps to prevent rate limiting and maintain a stable request flow.
    rpm_capacity_target_ratio: float = 0.995

    # None: Rich owns continuous progress and INFO logs only state transitions.
    # N: additionally emit a periodic PROGRESS event every N completed questions.
    # Setting this to 10 reproduces the spirit of the previous logging mode.
    progress_log_every: int | None = None

    # The factor by which the launch interval is increased after a failed request or rate limit
    launch_interval_backoff_factor: float = 1.25
    # The minimum amount of time in seconds to wait before retrying a failed request or after
    # encountering a rate limit. This helps to prevent overwhelming the server with rapid retries
    # and allows for a more controlled recovery from failures or rate limits.
    launch_interval_backoff_sec: float = 0.05

    def __post_init__(self) -> None:
        if self.initial_concurrency <= 0:
            raise ValueError("initial_concurrency must be greater than 0")

        if self.max_target_concurrency < self.initial_concurrency:
            raise ValueError("max_target_concurrency must be >= initial_concurrency")

        if self.initial_launch_interval_sec < 0:
            raise ValueError("initial_launch_interval_sec must be >= 0")

        if self.min_launch_interval_sec < 0:
            raise ValueError("min_launch_interval_sec must be >= 0")

        if self.max_launch_interval_sec < self.min_launch_interval_sec:
            raise ValueError(
                "max_launch_interval_sec must be >= min_launch_interval_sec"
            )

        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")

        if self.max_backoff_sec <= 0:
            raise ValueError("max_backoff_sec must be greater than 0")

        if self.successes_before_concurrency_increase <= 0:
            raise ValueError(
                "successes_before_concurrency_increase must be greater than 0"
            )

        if self.successes_before_rpm_probe < 0:
            raise ValueError("successes_before_rpm_probe must be >= 0")

        if not 0.0 < self.rpm_capacity_target_ratio <= 1.0:
            raise ValueError("rpm_capacity_target_ratio must be in (0, 1]")

        if self.progress_log_every is not None and self.progress_log_every <= 0:
            raise ValueError("progress_log_every must be > 0 or None")
