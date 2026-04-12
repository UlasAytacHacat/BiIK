from __future__ import annotations

import asyncio
import logging

from api.routes.convert import run_convert
from api.routes.embed import run_embed
from api.routes.extract import RateLimitError, run_extract
from api.routes.write import run_write
from src.job_store import JobStatus, StepStatus, job_store

logger = logging.getLogger(__name__)

# Groq rate limit — aynı anda max 1 extract işlemi
_extract_semaphore = asyncio.Semaphore(1)
# Genel pipeline — aynı anda max 3 CV işlenir
_pipeline_semaphore = asyncio.Semaphore(3)

# Her retry'da artan bekleme (saniye)
RETRY_DELAYS = [5, 15, 30, 60]


async def _run_extract_step(filename: str) -> dict:
    """Extract'ı semaphore + inter-request delay ile seri çalıştırır."""
    async with _extract_semaphore:
        await asyncio.sleep(5)  # Groq istekleri arası minimum bekleme
        return await run_extract(filename)


async def _run_with_retry(
    job_id: str,
    step_name: str,
    fn,
    filename: str,
) -> dict | None:
    """
    fn(filename) çağrısını RETRY_DELAYS listesine göre retry eder.
    Başarıda job_store adımı DONE/SKIPPED olarak işaretler, sonuç dict'i döner.
    Tüm retry'lar bitince adımı ERROR yapar ve None döner.
    RateLimitError alınca retry_after kadar bekler ve tekrar dener.
    """
    delays = [0] + RETRY_DELAYS  # (attempt=0, delay=0), (1, 5), ...

    for attempt, delay in enumerate(delays):
        if delay > 0:
            logger.warning(
                "[%s] %s retry %d/%d — %ds bekleniyor",
                job_id, step_name, attempt, len(RETRY_DELAYS), delay,
            )
            await asyncio.sleep(delay)

        try:
            result = await fn(filename)
            cached = result.get("cached", False)
            job_store.update_step(
                job_id,
                step_name,
                StepStatus.SKIPPED if cached else StepStatus.DONE,
                cached=cached,
            )
            return result

        except RateLimitError as exc:
            wait = exc.retry_after or RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning("[%s] Rate limit — %ds bekleniyor", job_id, wait)
            await asyncio.sleep(wait)
            continue  # sıradaki attempt'e geç (loop delay'i de eklenir)

        except Exception as exc:
            logger.error(
                "[%s] %s hata (deneme %d/%d): %s",
                job_id, step_name, attempt + 1, len(delays), exc,
            )
            if attempt == len(delays) - 1:
                job_store.update_step(job_id, step_name, StepStatus.ERROR, error=str(exc))
                return None
            # Son deneme değil — bir sonraki iterasyonda retry delay uygulanır

    return None  # tüm denemeler bitti


async def run_pipeline_for_job(job_id: str, upload_filename: str) -> None:
    """
    Tek bir CV için tam pipeline'ı çalıştırır:
      convert → extract → embed → write

    ingest adımı jobs.py'deki batch endpoint'te tamamlanmış olur.
    """
    async with _pipeline_semaphore:
        job = job_store.get(job_id)
        if job is None:
            logger.error("[%s] Job bulunamadı — iptal edildi", job_id)
            return

        # ------------------------------------------------------------------ convert
        job_store.update_step(job_id, "convert", StepStatus.RUNNING)
        result = await _run_with_retry(job_id, "convert", run_convert, upload_filename)
        if result is None:
            job_store.mark_failed(job_id, "convert başarısız")
            return
        data_filename: str = result["filename"]

        # ------------------------------------------------------------------ extract
        job = job_store.get(job_id)
        if job.status == JobStatus.FAILED:
            return

        job_store.update_step(job_id, "extract", StepStatus.RUNNING)
        result = await _run_with_retry(job_id, "extract", _run_extract_step, data_filename)
        if result is None:
            job_store.mark_failed(job_id, "extract başarısız")
            return
        output_filename: str = result["filename"]

        # ------------------------------------------------------------------ embed
        job = job_store.get(job_id)
        if job.status == JobStatus.FAILED:
            return

        job_store.update_step(job_id, "embed", StepStatus.RUNNING)
        result = await _run_with_retry(job_id, "embed", run_embed, output_filename)
        if result is None:
            job_store.mark_failed(job_id, "embed başarısız")
            return

        # ------------------------------------------------------------------ write
        job = job_store.get(job_id)
        if job.status == JobStatus.FAILED:
            return

        job_store.update_step(job_id, "write", StepStatus.RUNNING)
        result = await _run_with_retry(job_id, "write", run_write, output_filename)
        if result is None:
            job_store.mark_failed(job_id, "write başarısız")
            return

        job_store.mark_done(job_id)
        logger.info("[%s] Pipeline tamamlandı: %s", job_id, upload_filename)
