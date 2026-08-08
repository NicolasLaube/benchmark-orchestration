from enum import StrEnum


class RateLimitKind(StrEnum):
    RPM = "rpm"
    CONCURRENCY = "concurrency"
    GENERIC = "generic"


def classify_rate_limit_reason(
    reason: str | None,
) -> RateLimitKind:
    """
    Classifies the reason for a rate limit event based on the provided reason string.
    Returns one of "rpm", "concurrency", or "generic" based on the content of the reason string.

    Args:
        reason (str | None): The reason string provided by the inference client for the rate
        limit event. This string may contain information about the type of rate limit
        encountered.

    Returns:
        RateLimitKind: A classification of the rate limit reason, which can be one of:
            - "rpm": Indicates that the rate limit was due to exceeding the requests per minute
              (RPM) limit.
            - "concurrency": Indicates that the rate limit was due to exceeding the concurrency
              limit (i.e., too many in-flight requests).
            - "generic": Indicates that the rate limit reason could not be classified as either
                "rpm" or "concurrency" and is treated as a generic overload.
    """
    value = (reason or "").lower()

    if "rpm" in value or "request" in value or "minute" in value:
        return RateLimitKind.RPM

    if "concurrency" in value or "in_flight" in value or "in-flight" in value:
        return RateLimitKind.CONCURRENCY

    return RateLimitKind.GENERIC
