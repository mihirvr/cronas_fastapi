from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.job_api.app.dependencies import get_db, get_scheduler_store
from shared.config import get_settings
from shared.kafka_bus import KafkaBus
from shared.redis_store import RedisSchedulerStore
from shared.repository import JobRepository
from shared.schemas import JobCreate, JobResponse, JobRunResponse, JobUpdate

app = FastAPI(title="CronasFastAPI", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>CronasFastAPI Dashboard</title>
  <style>
    body { font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1f2937; }
    header { padding: 20px 28px; background: #0f172a; color: white; }
    main { padding: 24px 28px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .panel { background: white; border-radius: 14px; padding: 18px; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08); }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; font-size: 14px; vertical-align: top; }
    th { font-size: 12px; text-transform: uppercase; color: #6b7280; }
    .mono { font-family: Consolas, monospace; font-size: 12px; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: 12px; }
    .controls { margin-bottom: 18px; }
    button { background: #2563eb; color: white; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; }
    pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
    .notice { margin: 0 0 16px 0; padding: 12px 14px; background: #fff7ed; border-radius: 10px; color: #9a3412; }
  </style>
</head>
<body>
  <header>
    <h1>CronasFastAPI</h1>
    <p>Open this page to see what is stored in PostgreSQL.</p>
  </header>
  <main>
    <p class="notice" id="notice">If the tables are empty or missing, run <code>alembic upgrade head</code> first.</p>
    <div class="controls"><button onclick="loadData()">Refresh</button></div>
    <div class="grid">
      <section class="panel">
        <h2>Jobs table</h2>
        <table>
          <thead><tr><th>Job ID</th><th>Name</th><th>Status</th><th>Type</th><th>Next Run</th></tr></thead>
          <tbody id="jobs-body"></tbody>
        </table>
      </section>
      <section class="panel">
        <h2>job_runs table</h2>
        <table>
          <thead><tr><th>Run ID</th><th>Job ID</th><th>Attempt</th><th>Status</th><th>Result / Error</th></tr></thead>
          <tbody id="runs-body"></tbody>
        </table>
      </section>
    </div>
  </main>
  <script>
    async function loadData() {
      const response = await fetch('/dashboard-data');
      const data = await response.json();
      const notice = document.getElementById('notice');
      if (data.error) {
        notice.textContent = data.error;
      } else {
        notice.textContent = 'Showing the latest rows stored in PostgreSQL.';
      }
      const jobsBody = document.getElementById('jobs-body');
      const runsBody = document.getElementById('runs-body');
      jobsBody.innerHTML = data.jobs.map(job => `
        <tr>
          <td class="mono">${job.job_id}</td>
          <td>${job.name}</td>
          <td><span class="badge">${job.status}</span></td>
          <td>${job.schedule_type}</td>
          <td>${job.next_run_at ?? '-'}</td>
        </tr>
      `).join('');
      runsBody.innerHTML = data.runs.map(run => `
        <tr>
          <td class="mono">${run.run_id}</td>
          <td class="mono">${run.job_id}</td>
          <td>${run.attempt}</td>
          <td><span class="badge">${run.status}</span></td>
          <td><pre>${JSON.stringify(run.result_payload ?? run.error_message ?? '', null, 2)}</pre></td>
        </tr>
      `).join('');
    }
    loadData();
  </script>
</body>
</html>"""


@app.get("/dashboard-data")
def dashboard_data(db: Session = Depends(get_db)) -> dict:
    try:
        repo = JobRepository(db)
        jobs = [JobResponse.model_validate(job).model_dump(mode='json') for job in repo.list_jobs(limit=100)]
        runs = [JobRunResponse.model_validate(run).model_dump(mode='json') for run in repo.list_recent_runs(limit=100)]
        return {"jobs": jobs, "runs": runs}
    except SQLAlchemyError as exc:
        return {
            "jobs": [],
            "runs": [],
            "error": "Database is not ready yet. Start PostgreSQL and run 'alembic upgrade head'. Details: " + str(exc),
        }


@app.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db), scheduler: RedisSchedulerStore = Depends(get_scheduler_store)) -> JobResponse:
    repo = JobRepository(db)
    job = repo.create_job(payload)
    if job.next_run_at is not None:
        scheduler.schedule_job(job.job_id, job.next_run_at)
    return JobResponse.model_validate(job)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> JobResponse:
    repo = JobRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@app.patch("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: UUID, payload: JobUpdate, db: Session = Depends(get_db), scheduler: RedisSchedulerStore = Depends(get_scheduler_store)) -> JobResponse:
    repo = JobRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job = repo.update_job(job, payload)
    if job.next_run_at is not None:
        scheduler.schedule_job(job.job_id, job.next_run_at)
    return JobResponse.model_validate(job)


@app.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: UUID, db: Session = Depends(get_db), scheduler: RedisSchedulerStore = Depends(get_scheduler_store)) -> JobResponse:
    repo = JobRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job = repo.cancel_job(job)
    scheduler.mark_cancelled(job.job_id)
    return JobResponse.model_validate(job)


@app.post("/jobs/{job_id}/run-now")
def run_now(job_id: UUID, db: Session = Depends(get_db)) -> dict:
    repo = JobRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    run = repo.create_manual_run(job)
    message = repo.build_message(job, run)
    producer = KafkaBus().producer()
    producer.send(get_settings().jobs_run_topic, message)
    producer.flush()
    producer.close()
    return {"job_id": str(job.job_id), "run_id": str(run.run_id), "message": "Run published to Kafka"}


@app.get("/jobs/{job_id}/runs", response_model=list[JobRunResponse])
def list_runs(job_id: UUID, db: Session = Depends(get_db)) -> list[JobRunResponse]:
    repo = JobRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return [JobRunResponse.model_validate(run) for run in repo.list_runs(job_id)]
