# Architecture Reference

## End-to-End Lifecycle

The presentation describes this flow:

1. Client sends a scheduling request to the API gateway
2. Job service validates the request and writes durable state to PostgreSQL
3. Watcher polls Redis every 20 seconds for due work
4. Due jobs are published to Kafka topics
5. Executor services consume Kafka messages and run the job
6. Consumers update `job_runs` with the result
7. Retry and cancel flows are coordinated through Redis and Kafka

## Recommended Service Split

### API service

Responsibilities:

- accept create, update, cancel, runNow, and status requests
- validate job definitions and cron expressions
- persist durable job metadata
- write scheduling hints to Redis

### Watcher service

Responsibilities:

- poll Redis for due entries
- resolve job metadata when needed
- publish messages to Kafka run or retry topics
- avoid duplicate enqueue storms through atomic claim logic

### Executor service

Responsibilities:

- consume `jobs.run` and `jobs.retry`
- execute business work or dispatch to downstream handlers
- update `job_runs` and job state transitions
- route exhausted failures to `jobs.dlq`

## Topic Model

Use dedicated topics instead of one overloaded stream:

- `jobs.run`: first execution
- `jobs.retry`: transient failure re-attempts
- `jobs.dlq`: terminal failures for manual inspection

Suggested message fields:

- `job_id`
- `run_id`
- `attempt`
- `scheduled_at`
- `enqueued_at`
- `trace_id`
- `idempotency_key`
- `payload`

## Redis Role

Use Redis as fast scheduling and coordination state:

- sorted set for due jobs keyed by timestamp score
- cancellation marker keys with TTL
- ephemeral coordination keys for watcher claims or debouncing

Do not treat Redis as the only system of record. PostgreSQL should retain durable state.

## PostgreSQL Role

Persist durable entities:

- `jobs`
- `job_runs`
- optional `job_events`

Suggested durability rules:

- the source job definition always lives in PostgreSQL
- every execution attempt produces or updates a `job_runs` record
- terminal states should be queryable without scanning Kafka or Redis

## Reliability Notes

- Design for at-least-once semantics
- Make executors idempotent
- Commit Kafka offsets after durable state updates
- Keep retry policy explicit with `max_attempts`, backoff, and dead-letter routing
- Validate cancel checks both before execution starts and before retry scheduling

## Performance Notes

To move toward the target throughput:

- keep API handlers thin
- batch watcher publishes where possible
- partition Kafka topics to scale consumers
- index database queries on due-time and status columns
- consider time-based partitioning for large `job_runs` tables
