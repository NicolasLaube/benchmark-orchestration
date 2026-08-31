"""
This module defines data models for benchmark jobs and questions used in the orchestrator.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkRun:
    """Represents a benchmark job with its associated metadata."""

    id: str
    path: str
