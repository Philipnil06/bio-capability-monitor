"""Shared dataclasses for experiment records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TaskMode = Literal["benign", "adversarial"]
TaskCondition = Literal["benign", "adversarial", "benign_overuse", "partial_adversarial", "borderline"]
BorderlineProfile = Literal["minimal_path", "mild_validation_path"]
ProviderCalibrationProfile = Literal[
    "s1_benign_minimal",
    "s1_partial_minimal_attempt",
    "s1_partial_mild_probe",
    "s2_adversarial_same_tier_scope",
    "s2_adversarial_preserve_main",
    "s2_partial_minimal_attempt",
    "s2_partial_mild_probe",
    "s2_partial_same_tier_success",
    "s3_adversarial_preserve_main",
    "s3_partial_minimal_attempt",
    "s3_partial_mild_probe",
    "s3_partial_same_tier_success",
]


def infer_condition(mode: str | None, notes: str | None = None) -> TaskCondition:
    """Infer condition for old task/result records that lack structured metadata."""

    text = f"{mode or ''} {notes or ''}".lower()
    if "benign_overuse" in text or "benign overuse" in text:
        return "benign_overuse"
    if "partial_adversarial" in text or "partial adversarial" in text:
        return "partial_adversarial"
    if "borderline" in text or "ambiguous" in text:
        return "borderline"
    if mode == "adversarial":
        return "adversarial"
    return "benign"


def task_condition(task: Any) -> TaskCondition:
    """Return structured task condition, falling back to notes for older tasks."""

    condition = getattr(task, "condition", None)
    if condition:
        return condition
    return infer_condition(getattr(task, "mode", None), getattr(task, "notes", None))


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
    condition: TaskCondition | None = None
    borderline_profile: BorderlineProfile | None = None
    provider_calibration_profile: ProviderCalibrationProfile | None = None


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
    parse_error: str | None = None
    borderline_profile: BorderlineProfile | None = None
    provider_calibration_profile: ProviderCalibrationProfile | None = None


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


@dataclass(frozen=True)
class ViolationLabels:
    """Verifier-side semantic labels for boundary behavior."""

    attempted_violation: bool
    successful_violation: bool
    overuse_violation: bool
    ambiguous_violation: bool
    side_task_is_disallowed: bool
    true_violation: bool


@dataclass
class RunRecord:
    """Full JSONL record for one experiment run."""

    run_id: str
    timestamp: str
    task_id: str
    scenario_id: str
    mode: TaskMode
    condition: TaskCondition
    borderline_profile: BorderlineProfile | None
    provider_calibration_profile: ProviderCalibrationProfile | None
    builder_model: str
    monitor_model: str
    allowed_tier: int
    hidden_side_goal: str | None
    notes: str | None
    visible_prompt: str
    tool_trace: list[dict[str, Any]]
    final_output: str
    main_task_success: bool
    side_task_attempted: bool
    side_task_success: bool
    observed_tier: int
    excess_tier: int
    attempted_violation: bool
    successful_violation: bool
    overuse_violation: bool
    ambiguous_violation: bool
    side_task_is_disallowed: bool
    true_violation: bool
    monitor_required_tier: int
    monitor_observed_tier: int
    monitor_flagged: bool
    monitor_reason: str
    monitor_outcome: str
    valid_run: bool
    builder_raw_response: str | None = None
    builder_parse_error: str | None = None
    monitor_raw_response: str | None = None
    monitor_parse_error: str | None = None
    error: str | None = None
