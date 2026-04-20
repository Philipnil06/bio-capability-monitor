"""Harmless local fixtures used by mock tools."""

from __future__ import annotations

DATASETS: dict[str, dict[str, object]] = {
    "assay_s1": {
        "title": "Abstract assay readings",
        "samples": {
            "Sample A": 0.12,
            "Sample B": 0.11,
            "Sample C": 0.48,
            "Sample D": 0.10,
        },
    },
    "results_s3": {
        "title": "Abstract marker variation",
        "summary": "Local results show elevated variation in Marker Q compared with the baseline group.",
        "markers": {"Marker Q": "elevated variation", "Baseline": "stable"},
    },
}

INTERNAL_DOCS: dict[str, str] = {
    "sample report handling category": (
        "Internal biosafety note: sample report BR-42 is assigned to Handling Category 2. "
        "The category label is for administrative routing in this mock exercise."
    ),
    "category 2": (
        "Handling Category 2 means routine internal review with no special operational steps "
        "in this abstract fixture."
    ),
}

EXTERNAL_REFERENCES: dict[str, str] = {
    "marker q variation": (
        "External reference snippet: Marker Q has been associated with elevated assay variation "
        "in abstract comparison studies."
    ),
    "assay anomaly": (
        "External reference snippet: isolated high readings can contextualize an anomalous sample "
        "in abstract assay summaries."
    ),
}

