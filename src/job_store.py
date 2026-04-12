from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StepStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"  # cache hit


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


PIPELINE_STEPS = ["ingest", "convert", "extract", "embed", "write"]


@dataclass
class StepState:
    status: StepStatus = StepStatus.IDLE
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    cached: bool = False


@dataclass
class Job:
    job_id: str
    original_filename: str
    status: JobStatus = JobStatus.QUEUED
    steps: dict = field(default_factory=lambda: {
        step: StepState() for step in PIPELINE_STEPS
    })
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    current_step: Optional[str] = None


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, filename: str) -> Job:
        job = Job(job_id=job_id, original_filename=filename)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def update_step(
        self,
        job_id: str,
        step: str,
        status: StepStatus,
        error: str = None,
        cached: bool = False,
    ):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.steps[step].status = status
            job.steps[step].cached = cached
            if status == StepStatus.RUNNING:
                job.steps[step].started_at = time.time()
                job.current_step = step
                job.status = JobStatus.RUNNING
            elif status in (StepStatus.DONE, StepStatus.SKIPPED):
                job.steps[step].finished_at = time.time()
            elif status == StepStatus.ERROR:
                job.steps[step].error = error
                job.steps[step].finished_at = time.time()
                job.status = JobStatus.FAILED
                job.finished_at = time.time()

    def mark_done(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.DONE
                job.finished_at = time.time()
                job.current_step = None

    def mark_failed(self, job_id: str, reason: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.finished_at = time.time()


# Singleton
job_store = JobStore()
