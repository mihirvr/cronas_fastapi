from collections.abc import Generator

from shared.database import SessionLocal
from shared.redis_store import RedisSchedulerStore


def get_db() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_scheduler_store() -> RedisSchedulerStore:
    return RedisSchedulerStore()
