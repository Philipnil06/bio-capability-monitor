"""Small configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


AmbiguousViolationPolicy = Literal["exclude", "violation", "non_violation"]
DEFAULT_AMBIGUOUS_VIOLATION_POLICY: AmbiguousViolationPolicy = "exclude"
DEFAULT_OPENSOURCE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
DEFAULT_OPENSOURCE_BASE_URL = "http://localhost:8000/v1"


@dataclass(frozen=True)
class ProviderConfig:
    """Provider configuration from CLI and environment."""

    provider: str
    builder_model: str
    monitor_model: str
    base_url: str | None = None
    api_key: str | None = None
    deterministic_monitor_miss_rate: float = 0.0


def env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable."""

    return os.environ.get(name, default)


def ambiguous_violation_policy(default: AmbiguousViolationPolicy = DEFAULT_AMBIGUOUS_VIOLATION_POLICY) -> AmbiguousViolationPolicy:
    """Return how ambiguous verifier labels should be handled in hard-label metrics."""

    value = env("AMBIGUOUS_VIOLATION_POLICY", default)
    if value in {"exclude", "violation", "non_violation"}:
        return value
    return default
