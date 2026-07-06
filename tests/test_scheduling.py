from datetime import UTC, datetime

from shared.models import ScheduleType
from shared.scheduling import compute_initial_next_run


def test_immediate_job_is_due_now() -> None:
    result = compute_initial_next_run(ScheduleType.immediate, None, None)
    assert result.tzinfo is UTC


def test_delayed_job_uses_scheduled_time() -> None:
    scheduled = datetime(2030, 1, 1, tzinfo=UTC)
    result = compute_initial_next_run(ScheduleType.delayed, scheduled, None)
    assert result == scheduled


def test_cron_job_returns_future_time() -> None:
    result = compute_initial_next_run(ScheduleType.cron, None, '*/5 * * * *')
    assert result.tzinfo is UTC
