# CronasFastAPI

**A High-Throughput Distributed Task & Webhook Scheduler built with FastAPI, Kafka, Redis, and PostgreSQL.**

CronasFastAPI is an elite, production-grade distributed task scheduling system designed for scale, resilience, and high-performance throughput. Engineered to support massive volumes of task execution requests, the system provides a robust architecture capable of immediate, delayed, and cron-based scheduling with advanced retry semantics and dead-letter queue (DLQ) capabilities.

## System Architecture Overview

To handle massive request volumes efficiently, CronasFastAPI decouples the API control plane from the execution workers:

- **Apache Kafka** serves as the primary message bus bridging the decoupled layers, allowing thousands of job requests to be ingested per second and asynchronously farmed out to executor nodes.
- **Redis** is utilized for ephemeral locking, tracking job state in real time, and maintaining highly optimized scheduling cues.
- **PostgreSQL** guarantees strict durability, acting as the permanent source of truth for both job configurations and complete historical execution telemetry.

## Key Structural Highlights

CronasFastAPI is explicitly architected around a **synchronous, non-blocking offloading design**. 

Instead of relying on an asynchronous event loop that might suffer from CPU-bound starvation during high loads, standard FastAPI routes are implemented synchronously. They instantly hand off execution contexts directly to Apache Kafka topics (`cronas.run`, `cronas.retry`, `cronas.dlq`). This structural decision ensures that the system maintains sub-millisecond API response times and unyielding throughput, fully delegating heavy operational lifting to horizontally scalable executor consumers.

## Tech Stack Breakdown

* **Framework:** FastAPI
* **Message Broker & Queue:** Apache Kafka & Redis (using high-performance `confluent-kafka` for Python 3.12 compatibility and speed)
* **Database & Persistence:** PostgreSQL (SQLAlchemy)

## Local Scaffolding & Setup

The entire underlying infrastructure can be scaffolded instantly using Docker Compose.

### 1. Start Infrastructure
Run the following command to bring up the containerized infrastructure (`cronas-postgres`, `cronas-redis`, and `cronas-kafka`):

```bash
docker compose up -d
```
*Note: Kafka may take 10-20 seconds to be fully ready after boot.*

### 2. Prepare the Environment
Set up your virtual environment, install dependencies, and configure your secrets:

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 3. Initialize the Database Schema
Apply the Alembic migrations to set up the necessary PostgreSQL tables:

```bash
alembic upgrade head
```

### 4. Bootstrapping Kafka Topics (Optional)
Ensure the required topics (`cronas.run`, `cronas.retry`, `cronas.dlq`) exist. Make sure to set `PYTHONPATH` so the script can locate your config:

```bash
$env:PYTHONPATH="."
python scripts\bootstrap_topics.py
```

### 5. Running the Services
The system is divided into decoupled microservices. Run them in separate terminals:

**API Control Plane:**
```bash
uvicorn services.job_api.app.main:app --reload --host 127.0.0.1 --port 8000
```

**Watcher Process (polls Redis and enqueues to Kafka):**
```bash
python -m services.watcher.watcher
```

**Executor Process (consumes from Kafka and executes jobs):**
```bash
python -m services.executor.executor
```

The live operational dashboard is accessible at `http://127.0.0.1:8000/dashboard` and API documentation at `http://127.0.0.1:8000/docs`.
