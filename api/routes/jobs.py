from __future__ import annotations

import asyncio
import uuid
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.routes.ingest import save_upload
from src.job_store import StepStatus, job_store
from src.pipeline_runner import run_pipeline_for_job

router = APIRouter()


# ---------------------------------------------------------------------------
# Serileştirme yardımcısı
# ---------------------------------------------------------------------------

def _step_to_dict(step_name: str, step) -> dict:
    duration_ms = None
    if step.started_at and step.finished_at:
        duration_ms = round((step.finished_at - step.started_at) * 1000)
    return {
        "status": step.status.value,
        "cached": step.cached,
        "duration_ms": duration_ms,
        "error": step.error,
    }


def _job_to_dict(job) -> dict:
    return {
        "job_id": job.job_id,
        "filename": job.original_filename,
        "status": job.status.value,
        "current_step": job.current_step,
        "steps": {
            name: _step_to_dict(name, state)
            for name, state in job.steps.items()
        },
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }


# ---------------------------------------------------------------------------
# Endpoint'ler
# ---------------------------------------------------------------------------

@router.get("/jobs")
def get_jobs():
    """Tüm job'ların durumunu döner."""
    return {"jobs": [_job_to_dict(j) for j in job_store.all()]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Tek bir job'ın durumunu döner."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' bulunamadı.")
    return _job_to_dict(job)


@router.post("/jobs/batch")
async def batch_upload(files: List[UploadFile] = File(...)):
    """
    Çoklu dosya yükleme: her dosya için job oluşturur, pipeline'ı
    background task olarak başlatır ve job_id listesini hemen döner.
    Frontend bu id'lerle GET /jobs'u poll eder.
    """
    results = []

    for file in files:
        job_id = str(uuid.uuid4())

        # Dosyayı kaydet (job_id prefix'li)
        try:
            upload_filename = await save_upload(file, job_id)
        except ValueError as exc:
            # Desteklenmeyen uzantı — bu dosyayı atla
            continue
        except Exception as exc:
            # Disk hatası vb. — bu dosyayı atla
            continue

        # Job oluştur, ingest adımını tamamla
        job_store.create(job_id, file.filename)
        job_store.update_step(job_id, "ingest", StepStatus.RUNNING)
        job_store.update_step(job_id, "ingest", StepStatus.DONE)

        # Pipeline'ı background'da başlat
        asyncio.create_task(run_pipeline_for_job(job_id, upload_filename))

        results.append({
            "job_id": job_id,
            "filename": file.filename,
            "status": "queued",
        })

    return {"jobs": results}
