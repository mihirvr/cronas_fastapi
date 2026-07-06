from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from croniter import croniter

from shared.models import Job, ScheduleType


def utc_now() -> datetime:
    return datetime.now(UTC)


def compute_initial_next_run(schedule_type: ScheduleType, scheduled_at: datetime | None, cron_expr: str | None) -> datetime:
    now = utc_now()
    if schedule_type == ScheduleType.immediate:
        return now
    if schedule_type == ScheduleType.delayed:
        if scheduled_at is None:
            raise ValueError("scheduled_at is required for delayed jobs")
        return scheduled_at.astimezone(UTC)
    if not cron_expr:
        raise ValueError("cron is required for cron jobs")
    return croniter(cron_expr, now).get_next(datetime).astimezone(UTC)


def compute_followup_run(job: Job, reference_time: datetime | None = None) -> datetime | None:
    if job.schedule_type != ScheduleType.cron or not job.cron_expr:
        return None
    base = reference_time or utc_now()
    return croniter(job.cron_expr, base).get_next(datetime).astimezone(UTC)


def build_run_message(job: Job, run_id: str, attempt: int) -> dict:
    return {
        "job_id": str(job.job_id),
        "run_id": run_id,
        "attempt": attempt,
        "scheduled_at": job.next_run_at.isoformat() if job.next_run_at else None,
        "enqueued_at": utc_now().isoformat(),
        "idempotency_key": f"{job.job_id}:{attempt}:{run_id}",
        "payload": job.payload,
    }


def compute_retry_time(backoff_seconds: int) -> datetime:
    return utc_now() + timedelta(seconds=backoff_seconds)


def new_trace_id() -> str:
    return str(uuid4())
