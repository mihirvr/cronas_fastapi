from __future__ import annotations

import time
from uuid import UUID

from shared.config import get_settings
from shared.database import SessionLocal
from shared.kafka_bus import KafkaBus
from shared.redis_store import RedisSchedulerStore
from shared.repository import JobRepository


def run_once() -> None:
    settings = get_settings()
    scheduler = RedisSchedulerStore()
    bus = KafkaBus()
    producer = bus.producer()
    due_job_ids = scheduler.pop_due_jobs(time.time())

    if not due_job_ids:
        producer.flush()
        producer.close()
        return

    with SessionLocal() as session:
        repo = JobRepository(session)
        for raw_job_id in due_job_ids:
            job = repo.get_job(UUID(raw_job_id))
            if not job or scheduler.is_cancelled(job.job_id):
                continue
            attempt = len(repo.list_runs(job.job_id)) + 1
            run = repo.create_run(job, attempt=attempt)
            message = repo.build_message(job, run)
            producer.send(settings.jobs_run_topic, message)
            if job.next_run_at is not None:
                scheduler.schedule_job(job.job_id, job.next_run_at)
    producer.flush()
    producer.close()


def main() -> None:
    settings = get_settings()
    print('Watcher started. Make sure you already ran: python -m alembic upgrade head')
    print(f"Polling every {settings.watcher_poll_seconds} seconds")
    while True:
        run_once()
        time.sleep(settings.watcher_poll_seconds)


if __name__ == "__main__":
    main()
