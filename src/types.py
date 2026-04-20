"""Shared dataclasses for experiment records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TaskMode = Literal["benign", "adversarial"]


@dataclass(frozen=True)
class TaskSpec:
    """Static task definition."""

    task_id: str
    scenario_id: str
    mode: TaskMode
    visible_prompt: str
    allowed_tier: int
    expected_main_result: str
    dataset_id: str | None = None
    hidden_side_goal: str | None = None
    notes: str | None = None


@dataclass
class ToolCall:
    """Single tool call made by a builder."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_output: dict[str, Any]
    tier: int


@dataclass
class BuilderRunResult:
    """Builder output and trace."""

    final_output: str
    tool_trace: list[ToolCall] = field(default_factory=list)
    raw_response: str | None = None
    valid_run: bool = True
    error: str | None = None


@dataclass
class MonitorResult:
    """Monitor judgment."""

    required_tier: int
    observed_tier: int
    boundary_violation: bool
    unnecessary_actions: list[str]
    reason: str
    raw_response: str | None = None
    parse_error: str | None = None


@dataclass
class RunRecord:
    """Full JSONL record for one experiment run."""

    run_id: str
    timestamp: str
    task_id: str
    scenario_id: str
    mode: TaskMode
    builder_model: str
    monitor_model: str
    allowed_tier: int
    hidden_side_goal: str | None
    visible_prompt: str
    tool_trace: list[dict[str, Any]]
    final_output: str
    main_task_success: bool
    side_task_success: bool
    observed_tier: int
    monitor_required_tier: int
    monitor_observed_tier: int
    monitor_flagged: bool
    monitor_reason: str
    monitor_outcome: str
    valid_run: bool
    error: str | None = None

