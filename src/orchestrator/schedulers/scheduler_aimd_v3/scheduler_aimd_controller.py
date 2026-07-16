"""
This module implements the Adaptive AIMD (Additive Increase Multiplicative Decrease) controller,
which is a state machine that adjusts the target concurrency and launch interval based on observed
outcomes of attempts. The controller operates in different phases, including an initial "opaque RPM
probe" phase and a subsequent "adaptive" phase, where it responds to successes and failures to
optimize throughput while avoiding rate limits.

"""

import enum
from math import floor

from orchestrator.schedulers.common.classify_rate_limit_reason import (
    RateLimitKind,
    classify_rate_limit_reason,
)
from orchestrator.schedulers.common.scheduler_models import (
    AttemptOutcome,
    ControlUpdate,
)
from orchestrator.schedulers.scheduler_aimd_v3.scheduler_aimd_config import (
    AdaptiveAimdConfig,
)


class AIMDPhase(enum.Enum):
    OPAQUE_RPM_PROBE = "opaque_rpm_probe"
    ADAPTIVE = "adaptive"

    # to string method
    def __str__(self) -> str:
        return self.value


class AdaptiveAimdController:
    """The controller decides how to adjust the target concurrency and launch interval based on
    observed outcomes. It maintains the state of the scheduler, including the current phase,
    target concurrency, and launch interval."""

    def __init__(self, config: AdaptiveAimdConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        """Reset the controller state to its initial values."""
        # Target concurrency and launch interval are the primary control variables that the AIMD
        # controller adjusts based on observed outcomes.
        self.target_concurrency = self.config.initial_concurrency
        # rpm is inversely proportional to launch interval,
        # rpm = 60 / launch_interval_sec
        self.launch_interval_sec = self.config.initial_launch_interval_sec

        # The controller operates in different phases, which dictate how it responds to successes
        # and failures.
        # The "opaque_rpm_probe" phase is used to probe the system's RPM limit without prior
        # knowledge. The "adaptive" phase is the normal operating mode where the controller
        # adjusts concurrency and launch interval based on observed outcomes.
        self.phase = (
            AIMDPhase.OPAQUE_RPM_PROBE
            if self.config.successes_before_rpm_probe > 0
            else AIMDPhase.ADAPTIVE
        )

        # The following attributes track the state of the controller in response to
        # observed outcomes:
        self.success_since_last_limit = 0  # Counts consecutive successful attempts since the last
        # rate limit was observed.
        self.probe_success_count = 0  # Counts successful attempts during the RPM probe phase.
        self.structured_429_seen = (
            False  # Indicates if a structured 429 response has been observed.
        )
        self.estimated_rpm_limit: int | None = (
            None  # Estimated RPM limit based on observed outcomes.
        )
        self.estimated_concurrency_limit: int | None = (
            None  # Estimated concurrency limit based on observed outcomes.
        )

    def classify_rate_limit(
        self,
        outcome: AttemptOutcome,
    ) -> tuple[RateLimitKind, str | None]:
        """Classifies the type of rate limit encountered based on the outcome of an attempt.

        Args:
            outcome (AttemptOutcome): The outcome of the attempt that triggered the rate limit.
            Returns:
            tuple[RateLimitKind, str | None]: A tuple containing the classified rate limit kind and
            an optional reason for structured 429 responses.
        """
        kind = classify_rate_limit_reason(outcome.rate_limit_reason)

        if kind != RateLimitKind.GENERIC:
            # Easy case: If the rate limit reason can be classified as either RPM or concurrency,
            # return the classification along with any structured 429 reason.
            reason = (outcome.rate_limit_reason or "").lower()

            return (
                kind,
                self._mark_structured_429(reason),
            )

        # If the rate limit reason is generic, we need to infer the type of limit based on observed
        # metrics. If the number of in-flight requests is 1 or less, it indicates that the rate
        # limit is likely due to the RPM limit rather than concurrency.
        # If the observed launch RPM is close to the estimated RPM limit, we classify it as an RPM
        # limit. Otherwise, we classify it as a generic overload.

        if outcome.observed_in_flight <= 1:
            # If the number of in-flight requests is 1 or less, it indicates that the rate limit is
            # likely due to the RPM limit rather than concurrency. This is because a concurrency
            # limit would typically allow multiple in-flight requests, while an RPM limit would
            # restrict the rate of requests regardless of concurrency.
            return RateLimitKind.RPM, None

        if self.estimated_rpm_limit is not None and outcome.observed_launch_rpm >= int(
            0.90 * self.estimated_rpm_limit
        ):
            return RateLimitKind.RPM, None

        return RateLimitKind.GENERIC, None

    def on_rpm_limited(self, outcome: AttemptOutcome) -> ControlUpdate:
        """Handle an RPM limit event, adjusting the controller's state accordingly.

        Args:
            outcome (AttemptOutcome): The outcome of the attempt that triggered the RPM limit.

        Returns:
            ControlUpdate: A snapshot of the controller's state before the update.
        """
        update = self._snapshot("rpm_limit")

        if outcome.observed_launch_rpm > 0:
            # Update the estimated RPM limit based on the observed launch RPM, ensuring that it
            # does not increase if a lower limit has already been observed.
            candidate = max(1, outcome.observed_launch_rpm - 1)
            self.estimated_rpm_limit = (
                candidate
                if self.estimated_rpm_limit is None
                else min(self.estimated_rpm_limit, candidate)
            )

        if self.estimated_rpm_limit is not None:
            # Calculate the target RPM based on the estimated RPM limit and the configured capacity
            #  target ratio.
            target_rpm = max(
                1.0,
                self.estimated_rpm_limit * self.config.rpm_capacity_target_ratio,
            )
            learned_interval = 60.0 / target_rpm
        else:
            # If the estimated RPM limit is not available, we use a backoff strategy to increase the
            # launch interval. This helps to prevent overwhelming the server with rapid retries and
            # allows for a more controlled recovery from failures or rate limits.
            learned_interval = (
                self.launch_interval_sec * self.config.launch_interval_backoff_factor
                + self.config.launch_interval_backoff_sec
            )

        # Update the launch interval based on the learned interval, ensuring that it remains within
        # the configured minimum and maximum bounds. This helps to prevent the launch interval
        # from becoming too short or too long, which could lead to either overwhelming the server
        # or underutilizing resources.
        self.launch_interval_sec = min(
            self.config.max_launch_interval_sec,
            max(self.config.min_launch_interval_sec, learned_interval),
        )
        self.success_since_last_limit = 0
        self.probe_success_count = 0

        if self.phase == AIMDPhase.OPAQUE_RPM_PROBE:
            # If the controller is in the "opaque RPM probe" phase, we transition to the "adaptive"
            # phase after observing an RPM limit. This indicates that we have gathered enough
            # information about the RPM limit and can now operate in the adaptive phase.
            self.phase = AIMDPhase.ADAPTIVE
            self.target_concurrency = min(
                self.config.max_target_concurrency,
                max(self.target_concurrency, 2),
            )

        return update

    def on_concurrency_limited(
        self,
        outcome: AttemptOutcome,
    ) -> ControlUpdate:
        """
        Handle a concurrency limit event, adjusting the controller's state accordingly.

        Args:
            outcome (AttemptOutcome): The outcome of the attempt that triggered the concurrency
            limit.

        Returns:
            ControlUpdate: A snapshot of the controller's state before the update.
        """
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
        self.success_since_last_limit = 0
        self.probe_success_count = 0
        self.phase = AIMDPhase.ADAPTIVE
        return update

    def on_generic_overload(self) -> ControlUpdate:
        """
        Handle a generic overload event, adjusting the controller's state accordingly.

        Returns:
            ControlUpdate: A snapshot of the controller's state before the update.

        """
        update = self._snapshot("generic_overload")

        self.target_concurrency = max(
            1,
            floor(self.target_concurrency * self.config.generic_overload_concurrency_factor),
        )
        self.launch_interval_sec = min(
            self.config.max_launch_interval_sec,
            self.launch_interval_sec * self.config.launch_interval_backoff_factor
            + self.config.launch_interval_backoff_sec,
        )
        self.success_since_last_limit = 0
        self.probe_success_count = 0
        self.phase = AIMDPhase.ADAPTIVE
        return update

    def on_success(self) -> ControlUpdate | None:
        """
        Handle a successful attempt, adjusting the controller's state accordingly.

        Returns:
            ControlUpdate | None: A snapshot of the controller's state before the update, or None
            if no significant changes were made.
        """

        # If the controller is in the "opaque RPM probe" phase and has not yet observed a structured
        # 429 response, increment the probe success count. If the number of successful attempts
        # during the probe phase reaches the configured threshold, transition to the "adaptive"
        # phase and adjust the target concurrency accordingly.
        if self.phase == AIMDPhase.OPAQUE_RPM_PROBE and not self.structured_429_seen:
            self.probe_success_count += 1
            update = self._snapshot(
                "probe_completed",
                event="PROBE_COMPLETED",
            )

            # If the number of successful attempts during the probe phase reaches the configured
            # threshold, transition to the adaptive phase and adjust the target concurrency
            # accordingly.
            self.launch_interval_sec = max(
                self.config.min_launch_interval_sec,
                self.launch_interval_sec * self.config.probe_speedup_factor,
            )

            # Whave two possible exits from OPAQUE_RPM_PROBE
            # 1. We hit an RPM limit
            #    → estimated_rpm_limit learned
            #    → ADAPTIVE

            # 2. We observe enough successes without finding a limit
            #    → estimated_rpm_limit still None
            #    → ADAPTIVE
            # Because, else we would keep probing launch RPM but never really start additive
            # concurrency growth.
            if self.probe_success_count >= self.config.successes_before_rpm_probe:
                # Transition to the adaptive phase and adjust the target concurrency accordingly.
                self.phase = AIMDPhase.ADAPTIVE
                self.target_concurrency = min(
                    self.config.max_target_concurrency,
                    max(self.target_concurrency, 2),
                )
                return update

            return None

        self.success_since_last_limit += 1
        if self.success_since_last_limit < self.config.successes_before_concurrency_increase:
            return None

        update = self._snapshot("successes_before_concurrency_increase")
        concurrency_ceiling = (
            self.estimated_concurrency_limit
            if self.estimated_concurrency_limit is not None
            else self.config.max_target_concurrency
        )

        # Additive Increase: If the number of consecutive successful attempts since the last limit
        # has reached the configured threshold, increment the target concurrency by 1, up to the
        # estimated concurrency limit or the maximum target concurrency.
        if self.target_concurrency < concurrency_ceiling:
            self.target_concurrency += 1

        if self.estimated_rpm_limit is None:
            self.launch_interval_sec = max(
                self.config.min_launch_interval_sec,
                self.launch_interval_sec * self.config.success_speedup_factor,
            )

        self.success_since_last_limit = 0

        if (
            self.target_concurrency == update.old_concurrency
            and self.launch_interval_sec == update.old_interval
        ):
            return None

        return update

    def _mark_structured_429(self, reason: str) -> str | None:
        """
        Handle the detection of a structured 429 response, adjusting the controller's state
        accordingly.

        Returns:
            str | None: The reason for the structured 429, or None if it has already been seen.
        """
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
        """
        Create a snapshot of the controller's state before an update, capturing the cause and event
        type.

        Returns:
            ControlUpdate: A snapshot of the controller's state before the update.
        """
        return ControlUpdate(
            cause=cause,
            old_concurrency=self.target_concurrency,
            old_interval=self.launch_interval_sec,
            old_phase=self.phase,
            event=event,
        )
