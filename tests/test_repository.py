from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database import Base
from shared.models import JobStatus, ScheduleType
from shared.repository import JobRepository
from shared.schemas import JobCreate, RetryPolicy


def test_create_job_persists_expected_fields() -> None:
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    with Session() as session:
        repo = JobRepository(session)
        job = repo.create_job(
            JobCreate(
                name='demo',
                schedule_type=ScheduleType.delayed,
                scheduled_at=datetime(2030, 1, 1, tzinfo=UTC),
                payload={'message': 'hi'},
                retry_policy=RetryPolicy(max_attempts=4, backoff_seconds=10),
            )
        )

        assert job.name == 'demo'
        assert job.status == JobStatus.scheduled
        assert job.max_attempts == 4
