from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="CronasFastAPI")


class JobCreate(BaseModel):
    name: str
    schedule_type: str
    payload: dict
    scheduled_at: str | None = None
    cron: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs")
def create_job(job: JobCreate) -> dict[str, object]:
    return {"message": "Implement persistence and enqueue logic", "job": job.model_dump()}
