from __future__ import annotations

import json

from uuid import UUID

from shared.config import get_settings
from shared.database import SessionLocal
from shared.kafka_bus import KafkaBus
from shared.redis_store import RedisSchedulerStore
from shared.repository import JobRepository
from shared.scheduling import compute_retry_time


WORKER_ID = "executor-1"


def execute_payload(payload: dict, attempt: int) -> dict:
    if payload.get("force_fail"):
        raise RuntimeError("Payload requested a forced failure")
    fail_until = payload.get("fail_until_attempt")
    if isinstance(fail_until, int) and attempt < fail_until:
        raise RuntimeError(f"Simulated failure until attempt {fail_until}")
    return {"message": payload.get("message", "Job executed successfully"), "attempt": attempt}


def main() -> None:
    settings = get_settings()
    scheduler = RedisSchedulerStore()
    bus = KafkaBus()
    consumer = bus.consumer([settings.jobs_run_topic, settings.jobs_retry_topic], group_id="cronas-executor")
    producer = bus.producer()

    print("Executor started. Make sure you already ran: python -m alembic upgrade head")
    print("Waiting for Kafka messages...")

    while True:
        message = consumer.poll(1.0)
        if message is None:
            continue
        if message.error():
            continue

        payload = json.loads(message.value().decode("utf-8"))
        run_id = UUID(payload["run_id"])
        job_id = UUID(payload["job_id"])
        attempt = int(payload["attempt"])

        with SessionLocal() as session:
            repo = JobRepository(session)
            job = repo.get_job(job_id)
            if not job:
                consumer.commit()
                continue
            if scheduler.is_cancelled(job_id):
                repo.mark_run_cancelled(run_id, "Job cancelled before execution")
                consumer.commit()
                continue

            repo.mark_run_started(run_id, WORKER_ID)
            try:
                result = execute_payload(payload.get("payload", {}), attempt)
                repo.mark_run_succeeded(run_id, result_payload=result)
            except Exception as exc:
                if attempt < job.max_attempts:
                    repo.mark_run_retry_scheduled(run_id, str(exc))
                    retry_at = compute_retry_time(job.backoff_seconds)
                    repo.schedule_retry(job, retry_at)
                    scheduler.schedule_job(job.job_id, retry_at)
                else:
                    repo.mark_run_failed(run_id, str(exc), dead_letter=True)
                    producer.produce(settings.jobs_dlq_topic, value=json.dumps(payload).encode("utf-8"))
        producer.flush()
        consumer.commit()


if __name__ == "__main__":
    main()
