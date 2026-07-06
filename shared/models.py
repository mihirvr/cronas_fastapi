import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class ScheduleType(str, enum.Enum):
    immediate = "immediate"
    delayed = "delayed"
    cron = "cron"


class JobStatus(str, enum.Enum):
    scheduled = "scheduled"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    dead_lettered = "dead_lettered"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    retry_scheduled = "retry_scheduled"
    dead_lettered = "dead_lettered"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_type: Mapped[ScheduleType] = mapped_column(Enum(ScheduleType, native_enum=False), nullable=False)
    cron_expr: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, native_enum=False), nullable=False, default=JobStatus.scheduled)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    backoff_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    runs: Mapped[list['JobRun']] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobRun(Base):
    __tablename__ = "job_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, native_enum=False), nullable=False, default=RunStatus.queued)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job: Mapped[Job] = relationship(back_populates="runs")
