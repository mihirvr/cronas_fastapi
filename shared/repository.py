from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from shared.models import Job, JobRun, JobStatus, RunStatus, ScheduleType
from shared.schemas import JobCreate, JobUpdate
from shared.scheduling import build_run_message, compute_followup_run, compute_initial_next_run


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_job(self, payload: JobCreate) -> Job:
        next_run_at = compute_initial_next_run(payload.schedule_type, payload.scheduled_at, payload.cron)
        job = Job(
            name=payload.name,
            schedule_type=payload.schedule_type,
            cron_expr=payload.cron,
            payload=payload.payload,
            status=JobStatus.scheduled,
            scheduled_at=payload.scheduled_at.astimezone(UTC) if payload.scheduled_at else None,
            next_run_at=next_run_at,
            timezone=payload.timezone,
            max_attempts=payload.retry_policy.max_attempts,
            backoff_seconds=payload.retry_policy.backoff_seconds,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def list_jobs(self, limit: int = 100) -> list[Job]:
        stmt = select(Job).order_by(desc(Job.created_at)).limit(limit)
        return list(self.session.scalars(stmt))

    def get_job(self, job_id: UUID) -> Job | None:
        return self.session.get(Job, job_id)

    def list_runs(self, job_id: UUID) -> list[JobRun]:
        stmt = select(JobRun).where(JobRun.job_id == job_id).order_by(JobRun.created_at.desc())
        return list(self.session.scalars(stmt))

    def list_recent_runs(self, limit: int = 100) -> list[JobRun]:
        stmt = select(JobRun).order_by(desc(JobRun.created_at)).limit(limit)
        return list(self.session.scalars(stmt))

    def update_job(self, job: Job, payload: JobUpdate) -> Job:
        if payload.payload is not None:
            job.payload = payload.payload
        if payload.cron is not None:
            job.cron_expr = payload.cron
        if payload.scheduled_at is not None:
            job.scheduled_at = payload.scheduled_at.astimezone(UTC)
            if job.schedule_type == ScheduleType.delayed:
                job.next_run_at = job.scheduled_at
        if payload.max_attempts is not None:
            job.max_attempts = payload.max_attempts
        if payload.backoff_seconds is not None:
            job.backoff_seconds = payload.backoff_seconds
        self.session.commit()
        self.session.refresh(job)
        return job

    def cancel_job(self, job: Job) -> Job:
        job.status = JobStatus.cancelled
        self.session.commit()
        self.session.refresh(job)
        return job

    def create_run(self, job: Job, attempt: int, status: RunStatus = RunStatus.queued) -> JobRun:
        run = JobRun(
            job_id=job.job_id,
            attempt=attempt,
            status=status,
            idempotency_key=f"{job.job_id}:{attempt}:{uuid4()}",
        )
        self.session.add(run)
        job.status = JobStatus.queued
        if job.schedule_type == ScheduleType.cron:
            job.next_run_at = compute_followup_run(job, job.next_run_at)
        else:
            job.next_run_at = None
        self.session.commit()
        self.session.refresh(run)
        return run

    def create_manual_run(self, job: Job) -> JobRun:
        attempt = len(self.list_runs(job.job_id)) + 1
        return self.create_run(job, attempt=attempt)

    def schedule_retry(self, job: Job, retry_at: datetime) -> Job:
        job.status = JobStatus.scheduled
        job.next_run_at = retry_at
        self.session.commit()
        self.session.refresh(job)
        return job

    def mark_run_started(self, run_id: UUID, worker_id: str) -> JobRun:
        run = self.session.get(JobRun, run_id)
        if run is None:
            raise ValueError("Run not found")
        run.status = RunStatus.running
        run.started_at = datetime.now(UTC)
        run.worker_id = worker_id
        run.job.status = JobStatus.running
        self.session.commit()
        self.session.refresh(run)
        return run

    def mark_run_succeeded(self, run_id: UUID, result_payload: dict | None = None) -> JobRun:
        run = self.session.get(JobRun, run_id)
        if run is None:
            raise ValueError("Run not found")
        run.status = RunStatus.succeeded
        run.finished_at = datetime.now(UTC)
        run.result_payload = result_payload or {}
        run.job.status = JobStatus.completed if run.job.schedule_type != ScheduleType.cron else JobStatus.scheduled
        self.session.commit()
        self.session.refresh(run)
        return run

    def mark_run_failed(self, run_id: UUID, error_message: str, dead_letter: bool = False) -> JobRun:
        run = self.session.get(JobRun, run_id)
        if run is None:
            raise ValueError("Run not found")
        run.status = RunStatus.dead_lettered if dead_letter else RunStatus.failed
        run.finished_at = datetime.now(UTC)
        run.error_message = error_message
        run.job.status = JobStatus.dead_lettered if dead_letter else JobStatus.failed
        self.session.commit()
        self.session.refresh(run)
        return run

    def mark_run_retry_scheduled(self, run_id: UUID, error_message: str) -> JobRun:
        run = self.session.get(JobRun, run_id)
        if run is None:
            raise ValueError("Run not found")
        run.status = RunStatus.retry_scheduled
        run.finished_at = datetime.now(UTC)
        run.error_message = error_message
        run.job.status = JobStatus.scheduled
        self.session.commit()
        self.session.refresh(run)
        return run

    def mark_run_cancelled(self, run_id: UUID, reason: str) -> JobRun:
        run = self.session.get(JobRun, run_id)
        if run is None:
            raise ValueError("Run not found")
        run.status = RunStatus.cancelled
        run.finished_at = datetime.now(UTC)
        run.error_message = reason
        run.job.status = JobStatus.cancelled
        self.session.commit()
        self.session.refresh(run)
        return run

    def build_message(self, job: Job, run: JobRun) -> dict:
        return build_run_message(job, str(run.run_id), run.attempt)
