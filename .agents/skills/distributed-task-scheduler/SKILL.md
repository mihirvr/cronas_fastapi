---
name: distributed-task-scheduler
description: Design, scaffold, extend, and debug a distributed task scheduler built with Python microservices, FastAPI APIs, Kafka topics, Redis state, and PostgreSQL persistence. Use when Codex needs to work on scheduler backends, job lifecycle design, runNow/cancel APIs, cron and delayed scheduling, watcher polling, executor consumers, retry and dead-letter flows, or local development setup for this project.
---

# Distributed Task Scheduler

Use this skill to turn the project brief into implementation work for a Python-first distributed scheduler. Prefer it when the user is building or iterating on services such as the API layer, watcher, executor, retry handling, status tracking, or local infrastructure for Kafka, Redis, and PostgreSQL.

## Quick Start

1. Read [references/project-brief.md](references/project-brief.md) to recover the original goals, constraints, and supported job types.
2. Read [references/architecture.md](references/architecture.md) when designing service boundaries, Kafka topics, Redis usage, retries, or failure handling.
3. Read [references/api-and-data-model.md](references/api-and-data-model.md) when implementing FastAPI routes, request models, database tables, or job-run state transitions.
4. Use `scripts/scaffold_service.py` when the user needs a starter FastAPI API, watcher worker, or executor worker.
5. Copy from `assets/local-stack/` when the user needs a local compose stack or example environment values.

## Workflow

### 1. Clarify the task shape

Classify the request into one of these buckets:

- API work: creating or updating FastAPI endpoints, Pydantic models, validation, or runNow/cancel flows
- Scheduling work: due-job polling, delayed execution, cron expansion, or Redis watcher logic
- Execution work: Kafka consumers, retries, dead-letter routing, idempotency, or executor behavior
- Data work: PostgreSQL schema design, indexes, partitions, job state transitions, or observability tables
- Dev environment work: local Docker stack, config wiring, environment variables, or service bootstrapping

### 2. Keep the system invariants intact

Preserve these assumptions unless the user explicitly wants a redesign:

- Support immediate, future-dated, and cron jobs
- Favor availability over strict consistency
- Target at-least-once execution, not exactly-once delivery
- Treat idempotency as an application concern for executors
- Use Kafka topics for run, retry, and dead-letter flow separation
- Use Redis for fast scheduling state and cancellation markers
- Persist source-of-truth job and run status in PostgreSQL

### 3. Implement by service boundary

When coding, keep ownership clean:

- API service: accept create, update, cancel, runNow, and status requests
- Watcher service: find due work from Redis and enqueue Kafka messages
- Executor service: consume Kafka topics, run work, update `job_runs`, and schedule retries
- Shared models: centralize enums, job payload schema, retry metadata, and topic naming

### 4. Validate behavior, not only syntax

For any meaningful change, verify:

- immediate jobs can be enqueued without waiting for the poll window
- future jobs become runnable at or after `scheduled_at`
- cron jobs compute the next fire time after each successful enqueue
- cancelled jobs do not execute if a cancellation marker exists
- failed jobs move to retry or dead-letter according to policy
- repeated delivery does not corrupt state if the executor sees the same message twice

## Design Guidance

### FastAPI conventions

- Use FastAPI for synchronous control-plane APIs only; keep long-running job execution out of request handlers
- Define strict request and response models with Pydantic
- Separate route, service, repository, and messaging concerns
- Return stable job ids and expose job status through read APIs

### Kafka conventions

- Keep separate topics for `jobs.run`, `jobs.retry`, and `jobs.dlq`
- Include `job_id`, `run_id`, attempt number, scheduled time, and an idempotency key in every message
- Prefer explicit retry metadata over implicit consumer timing
- Commit offsets only after durable status updates succeed

### Redis conventions

- Use sorted sets or equivalent score-based structures for due-time polling
- Use keys with TTL for cancellation or short-lived coordination flags
- Keep Redis as acceleration state, not the long-term system of record

### PostgreSQL conventions

- Store durable job definitions and execution history
- Index by `job_id`, `status`, `scheduled_at`, and `next_run_at`
- Keep a separate `job_runs` table for attempts and terminal outcomes
- Consider partitioning `job_runs` by time in higher-throughput deployments

## Implementation Notes

- If the repo is empty or only partially scaffolded, start with the bundled scaffolding script instead of recreating boilerplate by hand.
- If the user asks for the high-level design from the presentation, summarize from the references instead of reopening the original PDF/PPT unless needed.
- If the user asks for future enhancements, bias toward DAG support, multi-tenancy, priority queues, and a monitoring dashboard, since those are already identified as follow-on work.

## Bundled Resources

### `references/project-brief.md`

Use for the original project scope, throughput targets, latency goals, and supported user-facing features.

### `references/architecture.md`

Use for service decomposition, Kafka topic responsibilities, Redis polling, retries, and end-to-end flow.

### `references/api-and-data-model.md`

Use for suggested FastAPI endpoints, request shapes, table outlines, and status lifecycle modeling.

### `scripts/scaffold_service.py`

Run to generate a minimal Python starter for one service:

```powershell
python scripts/scaffold_service.py --kind api --output .\services\job_api
python scripts/scaffold_service.py --kind watcher --output .\services\watcher
python scripts/scaffold_service.py --kind executor --output .\services\executor
```

### `assets/local-stack/`

Copy when the user needs a local development stack with Kafka, Redis, and PostgreSQL plus example environment variables.
