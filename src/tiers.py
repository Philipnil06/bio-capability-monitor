"""Capability tier definitions."""

from __future__ import annotations

from enum import IntEnum


class CapabilityTier(IntEnum):
    """Ordered capability tiers used by the experiment."""

    ANALYSIS_ONLY = 1
    INTERNAL_BIO_RETRIEVAL = 2
    EXTERNAL_BIO_RETRIEVAL = 3
    DESIGN_ADJACENT = 4
    SYNTHESIS_ADJACENT = 5


TIER_NAMES: dict[int, str] = {
    1: "Analysis only",
    2: "Internal bio retrieval",
    3: "External bio retrieval",
    4: "Design-adjacent",
    5: "Synthesis-adjacent",
}


def tier_name(tier: int) -> str:
    """Return a human-readable tier name."""

    return TIER_NAMES.get(tier, f"Unknown tier {tier}")

