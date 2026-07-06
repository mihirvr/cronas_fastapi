from __future__ import annotations

from datetime import datetime
from uuid import UUID

from redis import Redis

from shared.config import get_settings


class RedisSchedulerStore:
    def __init__(self) -> None:
        self.client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        self.schedule_key = "cronas:scheduled_jobs"

    def schedule_job(self, job_id: UUID, run_at: datetime) -> None:
        self.client.zadd(self.schedule_key, {str(job_id): run_at.timestamp()})

    def remove_job(self, job_id: UUID) -> None:
        self.client.zrem(self.schedule_key, str(job_id))

    def pop_due_jobs(self, now_ts: float) -> list[str]:
        due = self.client.zrangebyscore(self.schedule_key, min="-inf", max=now_ts)
        if due:
            self.client.zrem(self.schedule_key, *due)
        return due

    def mark_cancelled(self, job_id: UUID, ttl_seconds: int = 86400) -> None:
        self.client.setex(f"cronas:cancelled:{job_id}", ttl_seconds, "1")
        self.remove_job(job_id)

    def is_cancelled(self, job_id: UUID) -> bool:
        return self.client.exists(f"cronas:cancelled:{job_id}") == 1
