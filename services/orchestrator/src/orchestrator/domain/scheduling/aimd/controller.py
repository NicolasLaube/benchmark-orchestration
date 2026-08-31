import enum
from math import floor

from orchestrator.domain.scheduling.aimd.config import AdaptiveAimdSchedulerConfig
from orchestrator.domain.scheduling.common.classify_rate_limit_reason import (
    RateLimitKind,
    classify_rate_limit_reason,
)
from orchestrator.domain.scheduling.common.models import AttemptOutcome, ControlUpdate


class AIMDPhase(enum.Enum):
    OPAQUE_RPM_PROBE = "opaque_rpm_probe"
    ADAPTIVE = "adaptive"

    def __str__(self) -> str:
        return self.value


class AdaptiveAimdController:
    """Pure state machine controlling concurrency and request launch rate."""

    def __init__(self, config: AdaptiveAimdSchedulerConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self.target_concurrency = self.config.initial_concurrency
        self.launch_interval_sec = self.config.initial_launch_interval_sec
        self.phase = (
            AIMDPhase.OPAQUE_RPM_PROBE
            if self.config.successes_before_rpm_probe > 0
            else AIMDPhase.ADAPTIVE
        )
        self.success_since_last_limit = 0
        self.probe_success_count = 0
        self.structured_429_seen = False
        self.estimated_rpm_limit: int | None = None
        self.estimated_concurrency_limit: int | None = None

    def observability_fields(self) -> dict[str, object]:
        return {
            "target_concurrency": self.target_concurrency,
            "launch_interval_sec": f"{self.launch_interval_sec:.2f}",
            "phase": self.phase,
            "estimated_rpm_limit": self.estimated_rpm_limit,
            "estimated_concurrency_limit": self.estimated_concurrency_limit,
            "structured_429_seen": self.structured_429_seen,
        }

    def classify_rate_limit(
        self,
        outcome: AttemptOutcome,
    ) -> tuple[RateLimitKind, str | None]:
        kind = classify_rate_limit_reason(outcome.rate_limit_reason)

        if kind != RateLimitKind.GENERIC:
            reason = (outcome.rate_limit_reason or "").lower()
            return kind, self._mark_structured_429(reason)

        if outcome.observed_in_flight <= 1:
            return RateLimitKind.RPM, None

        close_to_rpm_limit = (
            self.estimated_rpm_limit is not None
            and outcome.observed_launch_rpm >= int(0.90 * self.estimated_rpm_limit)
        )
        if close_to_rpm_limit:
            return RateLimitKind.RPM, None

        return RateLimitKind.GENERIC, None

    def on_rpm_limited(self, outcome: AttemptOutcome) -> ControlUpdate:
        update = self._snapshot("rpm_limit")
        self._learn_rpm_limit(outcome.observed_launch_rpm)

        if self.estimated_rpm_limit is None:
            learned_interval = (
                self.launch_interval_sec * self.config.launch_interval_backoff_factor
                + self.config.launch_interval_backoff_sec
            )
        else:
            target_rpm = max(
                1.0,
                self.estimated_rpm_limit * self.config.rpm_capacity_target_ratio,
            )
            learned_interval = 60.0 / target_rpm

        self.launch_interval_sec = min(
            self.config.max_launch_interval_sec,
            max(self.config.min_launch_interval_sec, learned_interval),
        )
        self._reset_success_counters()

        if self.phase == AIMDPhase.OPAQUE_RPM_PROBE:
            self.phase = AIMDPhase.ADAPTIVE
            self.target_concurrency = min(
                self.config.max_target_concurrency,
                max(self.target_concurrency, 2),
            )

        return update

    def on_concurrency_limited(self, outcome: AttemptOutcome) -> ControlUpdate:
        update = self._snapshot("concurrency_limit")
        candidate = max(1, outcome.observed_in_flight - 1)
        self.estimated_concurrency_limit = (
            candidate
            if self.estimated_concurrency_limit is None
            else min(self.estimated_concurrency_limit, candidate)
        )
        self.target_concurrency = min(
            self.target_concurrency,
            self.estimated_concurrency_limit,
        )
        self._reset_success_counters()
        self.phase = AIMDPhase.ADAPTIVE
        return update

    def on_generic_overload(self) -> ControlUpdate:
        update = self._snapshot("generic_overload")
        self.target_concurrency = max(
            1,
            floor(
                self.target_concurrency
                * self.config.generic_overload_concurrency_factor
            ),
        )
        self.launch_interval_sec = min(
            self.config.max_launch_interval_sec,
            self.launch_interval_sec * self.config.launch_interval_backoff_factor
            + self.config.launch_interval_backoff_sec,
        )
        self._reset_success_counters()
        self.phase = AIMDPhase.ADAPTIVE
        return update

    def on_success(self) -> ControlUpdate | None:
        if self.phase == AIMDPhase.OPAQUE_RPM_PROBE and not self.structured_429_seen:
            return self._on_probe_success()

        self.success_since_last_limit += 1
        if (
            self.success_since_last_limit
            < self.config.successes_before_concurrency_increase
        ):
            return None

        update = self._snapshot("successes_before_concurrency_increase")
        ceiling = (
            self.estimated_concurrency_limit
            if self.estimated_concurrency_limit is not None
            else self.config.max_target_concurrency
        )
        if self.target_concurrency < ceiling:
            self.target_concurrency += 1

        if self.estimated_rpm_limit is None:
            self.launch_interval_sec = max(
                self.config.min_launch_interval_sec,
                self.launch_interval_sec * self.config.success_speedup_factor,
            )

        self.success_since_last_limit = 0
        unchanged = (
            self.target_concurrency == update.old_concurrency
            and self.launch_interval_sec == update.old_interval
        )
        return None if unchanged else update

    def _on_probe_success(self) -> ControlUpdate | None:
        self.probe_success_count += 1
        update = self._snapshot("probe_completed", event="PROBE_COMPLETED")
        self.launch_interval_sec = max(
            self.config.min_launch_interval_sec,
            self.launch_interval_sec * self.config.probe_speedup_factor,
        )

        if self.probe_success_count < self.config.successes_before_rpm_probe:
            return None

        self.phase = AIMDPhase.ADAPTIVE
        self.target_concurrency = min(
            self.config.max_target_concurrency,
            max(self.target_concurrency, 2),
        )
        return update

    def _learn_rpm_limit(self, observed_launch_rpm: int) -> None:
        if observed_launch_rpm <= 0:
            return

        candidate = max(1, observed_launch_rpm - 1)
        self.estimated_rpm_limit = (
            candidate
            if self.estimated_rpm_limit is None
            else min(self.estimated_rpm_limit, candidate)
        )

    def _reset_success_counters(self) -> None:
        self.success_since_last_limit = 0
        self.probe_success_count = 0

    def _mark_structured_429(self, reason: str) -> str | None:
        if self.structured_429_seen:
            return None

        self.structured_429_seen = True
        self.phase = AIMDPhase.ADAPTIVE
        return reason

    def _snapshot(
        self,
        cause: str,
        *,
        event: str = "CONTROL_UPDATE",
    ) -> ControlUpdate:
        return ControlUpdate(
            cause=cause,
            old_concurrency=self.target_concurrency,
            old_interval=self.launch_interval_sec,
            old_phase=self.phase,
            event=event,
        )
