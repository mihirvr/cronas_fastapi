# API And Data Model

## Suggested FastAPI Endpoints

### Jobs

- `POST /jobs`
  Create an immediate, delayed, or cron job.

- `GET /jobs/{job_id}`
  Fetch job definition and latest known state.

- `PATCH /jobs/{job_id}`
  Update mutable fields such as payload, schedule, or retry policy.

- `POST /jobs/{job_id}/cancel`
  Mark a job cancelled and set Redis cancellation state.

- `POST /jobs/{job_id}/run-now`
  Enqueue an immediate run even if the job also has a future or cron schedule.

- `GET /jobs/{job_id}/runs`
  List execution attempts from `job_runs`.

## Request Shape

Example create request:

```json
{
  "name": "send-reminder-email",
  "schedule_type": "cron",
  "cron": "*/5 * * * *",
  "scheduled_at": null,
  "timezone": "UTC",
  "payload": {
    "template": "reminder",
    "user_id": "123"
  },
  "retry_policy": {
    "max_attempts": 5,
    "backoff_seconds": 30
  }
}
```

## Suggested Tables

### `jobs`

Columns:

- `job_id` UUID primary key
- `name`
- `schedule_type` enum: `immediate`, `delayed`, `cron`
- `cron_expr` nullable
- `payload` JSONB
- `status` enum: `scheduled`, `running`, `completed`, `failed`, `cancelled`, `dead_lettered`
- `scheduled_at`
- `next_run_at`
- `timezone`
- `max_attempts`
- `backoff_seconds`
- `created_at`
- `updated_at`

### `job_runs`

Columns:

- `run_id` UUID primary key
- `job_id` foreign key
- `attempt`
- `status` enum: `queued`, `running`, `succeeded`, `failed`, `retry_scheduled`, `dead_lettered`, `cancelled`
- `started_at`
- `finished_at`
- `error_message`
- `worker_id`
- `idempotency_key`
- `trace_id`
- `result_payload` JSONB

## State Transitions

Common flow:

1. `scheduled`
2. `queued`
3. `running`
4. one of `succeeded`, `retry_scheduled`, `dead_lettered`, or `cancelled`

## FastAPI Implementation Guidance

- Keep route models separate from ORM models
- Normalize schedule fields so only the relevant combination is accepted
- Validate cron syntax before persistence
- Generate `run_id` at enqueue time, not only at completion time
- Record executor failures with enough metadata for later replay
