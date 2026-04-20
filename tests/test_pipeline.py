from src.builder import Builder
from src.monitor import Monitor
from src.tasks import load_tasks
from src.verify import check_main_task_success, check_side_task_success, compute_observed_tier


def task_by_id(task_id: str):
    return next(task for task in load_tasks() if task.task_id == task_id)


def test_tier_computation_uses_max_tool_tier() -> None:
    task = task_by_id("S3B")
    result = Builder().run(task)

    assert compute_observed_tier(result) == 5


def test_side_task_verification() -> None:
    benign = Builder().run(task_by_id("S2A"))
    adversarial = Builder().run(task_by_id("S2B"))

    assert check_side_task_success(task_by_id("S2A"), benign) is False
    assert check_side_task_success(task_by_id("S2B"), adversarial) is True


def test_mock_benign_run_is_true_negative() -> None:
    task = task_by_id("S1A")
    builder_result = Builder().run(task)
    monitor_result = Monitor().run(task, builder_result)

    assert check_main_task_success(task, builder_result) is True
    assert check_side_task_success(task, builder_result) is False
    assert monitor_result.boundary_violation is False


def test_mock_adversarial_run_is_true_positive() -> None:
    task = task_by_id("S3B")
    builder_result = Builder().run(task)
    monitor_result = Monitor().run(task, builder_result)

    assert check_main_task_success(task, builder_result) is True
    assert check_side_task_success(task, builder_result) is True
    assert monitor_result.boundary_violation is True
