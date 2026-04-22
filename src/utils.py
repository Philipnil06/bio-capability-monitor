"""Utility helpers for JSONL and dataclass serialization."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses recursively into JSON-friendly values."""

    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object from raw model text, tolerating code fences or trailing prose."""

    text = raw.strip()
    if not text:
        raise ValueError("Model returned an empty response.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    if parsed is not None:
        raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}.")

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        parsed = json.loads(fence.group(1))
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected a JSON object in fenced block, got {type(parsed).__name__}.")
        return parsed

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")
    decoder = json.JSONDecoder()
    parsed, _ = decoder.raw_decode(text[start:])
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}.")
    return parsed


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a single JSON object to a JSONL file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file."""

    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
