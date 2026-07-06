from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from shared.models import JobStatus, RunStatus, ScheduleType


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=20)
    backoff_seconds: int = Field(default=30, ge=1, le=3600)


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    schedule_type: ScheduleType
    payload: dict = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    cron: str | None = None
    timezone: str = "UTC"
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    @model_validator(mode="after")
    def validate_schedule_fields(self) -> 'JobCreate':
        if self.schedule_type == ScheduleType.immediate and (self.scheduled_at or self.cron):
            raise ValueError("Immediate jobs must not include scheduled_at or cron")
        if self.schedule_type == ScheduleType.delayed and not self.scheduled_at:
            raise ValueError("Delayed jobs require scheduled_at")
        if self.schedule_type == ScheduleType.cron and not self.cron:
            raise ValueError("Cron jobs require cron")
        return self


class JobUpdate(BaseModel):
    payload: dict | None = None
    scheduled_at: datetime | None = None
    cron: str | None = None
    max_attempts: int | None = Field(default=None, ge=1, le=20)
    backoff_seconds: int | None = Field(default=None, ge=1, le=3600)


class JobResponse(BaseModel):
    job_id: UUID
    name: str
    schedule_type: ScheduleType
    cron_expr: str | None
    payload: dict
    status: JobStatus
    scheduled_at: datetime | None
    next_run_at: datetime | None
    timezone: str
    max_attempts: int
    backoff_seconds: int

    model_config = {"from_attributes": True}


class JobRunResponse(BaseModel):
    run_id: UUID
    job_id: UUID
    attempt: int
    status: RunStatus
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    worker_id: str | None
    result_payload: dict | None

    model_config = {"from_attributes": True}
