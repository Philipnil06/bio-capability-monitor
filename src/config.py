"""Small configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    """Provider configuration from CLI and environment."""

    provider: str
    builder_model: str
    monitor_model: str
    base_url: str | None = None
    api_key: str | None = None
    mock_monitor_miss_rate: float = 0.0


def env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable."""

    return os.environ.get(name, default)

