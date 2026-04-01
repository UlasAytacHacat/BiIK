from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path

import fitz
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.routes.embed import _already_embedded, get_embedder
from api.routes.extract import get_extractor
from api.routes.write import get_writer
from src.schema import GraphData

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

# Per-step timeout in seconds.
# Timeout on attempt 1 triggers one retry from scratch.
# Any failure on attempt 2 → log + skip to next CV.
STEP_TIMEOUTS = {
    "convert": 60,
    "extract": 300,
    "embed": 180,
    "write": 120,
}

router = APIRouter()


# ---------------------------------------------------------------------------
# Step implementations (sync — run via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _do_convert(upload_filename: str) -> str:
    """Convert uploaded file → data/{stem}.json. Returns data filename."""
    src = UPLOADS_DIR / upload_filename
    stem = src.stem
    suffix = src.suffix.lower()

    if suffix == ".json":
        dest = DATA_DIR / src.name
        shutil.copy2(src, dest)
        return src.name

    if suffix == ".pdf":
        doc = fitz.open(str(src))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        dest_name = f"{stem}.json"
        (DATA_DIR / dest_name).write_text(
            json.dumps({"text": text, "annotations": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        return dest_name

    raise ValueError(f"Desteklenmeyen dosya türü: '{suffix}'")


def _do_extract(data_filename: str) -> str:
    """Extract graph from data JSON → output/{stem}_graph.json. Returns output filename."""
    src = DATA_DIR / data_filename
    stem = Path(data_filename).stem
    output_path = OUTPUT_DIR / f"{stem}_graph.json"

    if output_path.exists():
        return output_path.name

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("text", "")
    if not text.strip():
        raise ValueError("CV metni boş.")

    extractor = get_extractor()
    graph_data: GraphData = extractor.extract(text, data.get("annotations", []))

    output_path.write_text(
        json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path.name


def _do_embed(output_filename: str) -> None:
    """Add embeddings to graph JSON in-place."""
    src = OUTPUT_DIR / output_filename
    graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))

    if _already_embedded(graph_data):
        return

    embedder = get_embedder()
    graph_data = embedder.embed(graph_data)

    src.write_text(
        json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


def _do_write(output_filename: str) -> None:
    """Write graph to Memgraph and create sentinel file."""
    src = OUTPUT_DIR / output_filename
    sentinel = OUTPUT_DIR / (Path(output_filename).stem + ".written")

    if sentinel.exists():
        return

    graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))
    writer = get_writer()
    writer.write(graph_data, output_filename)
    sentinel.touch()


def _cleanup_for_retry(upload_filename: str) -> None:
    """Remove partial output files before retrying a CV from scratch."""
    stem = Path(upload_filename).stem
    # Remove extract output so the step runs fresh; convert is fast and has no cache.
    for path in [DATA_DIR / f"{stem}.json", OUTPUT_DIR / f"{stem}_graph.json"]:
        try:
            if path.exists():
                path.unlink()
                logger.info("Retry için temizlendi: %s", path)
        except Exception as exc:
            logger.warning("Temizleme başarısız %s: %s", path, exc)


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Pipeline async generator
# ---------------------------------------------------------------------------

async def _process_all(filenames: list[str]):
    """
    Async generator that yields SSE-formatted strings.

    Retry policy:
    - Timeout on attempt 1  → clean up partial files, retry from scratch once.
    - Any failure on attempt 2 (or non-timeout error on attempt 1) → log + skip CV.
    """
    success_count = 0
    failed_count = 0

    for upload_filename in filenames:
        cv_success = False
        retry = False  # becomes True when a timeout is detected on attempt 1

        for attempt in range(1, 3):
            # Only run attempt 2 if attempt 1 timed out
            if attempt == 2 and not retry:
                break

            if attempt == 1:
                yield _sse({"type": "cv_start", "filename": upload_filename})
            else:
                yield _sse({"type": "cv_retry", "filename": upload_filename})
                _cleanup_for_retry(upload_filename)

            data_filename: str | None = None
            output_filename: str | None = None
            failed_step: str | None = None
            step_error: str | None = None
            attempt_timed_out = False

            # ---- convert ----
            if failed_step is None:
                yield _sse({"type": "step_start", "filename": upload_filename, "step": "convert"})
                try:
                    data_filename = await asyncio.wait_for(
                        asyncio.to_thread(_do_convert, upload_filename),
                        timeout=STEP_TIMEOUTS["convert"],
                    )
                    yield _sse({"type": "step_done", "filename": upload_filename, "step": "convert"})
                except asyncio.TimeoutError:
                    attempt_timed_out = True
                    step_error = "Zaman aşımı"
                    failed_step = "convert"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "convert", "error": step_error, "is_timeout": True})
                    logger.warning("[%s] deneme %d convert: zaman aşımı", upload_filename, attempt)
                except Exception as exc:
                    step_error = str(exc)
                    failed_step = "convert"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "convert", "error": step_error, "is_timeout": False})
                    logger.error("[%s] deneme %d convert: %s", upload_filename, attempt, exc)

            # ---- extract ----
            if failed_step is None:
                yield _sse({"type": "step_start", "filename": upload_filename, "step": "extract"})
                try:
                    output_filename = await asyncio.wait_for(
                        asyncio.to_thread(_do_extract, data_filename),
                        timeout=STEP_TIMEOUTS["extract"],
                    )
                    yield _sse({"type": "step_done", "filename": upload_filename, "step": "extract"})
                except asyncio.TimeoutError:
                    attempt_timed_out = True
                    step_error = "Zaman aşımı"
                    failed_step = "extract"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "extract", "error": step_error, "is_timeout": True})
                    logger.warning("[%s] deneme %d extract: zaman aşımı", upload_filename, attempt)
                except Exception as exc:
                    step_error = str(exc)
                    failed_step = "extract"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "extract", "error": step_error, "is_timeout": False})
                    logger.error("[%s] deneme %d extract: %s", upload_filename, attempt, exc)

            # ---- embed ----
            if failed_step is None:
                yield _sse({"type": "step_start", "filename": upload_filename, "step": "embed"})
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(_do_embed, output_filename),
                        timeout=STEP_TIMEOUTS["embed"],
                    )
                    yield _sse({"type": "step_done", "filename": upload_filename, "step": "embed"})
                except asyncio.TimeoutError:
                    attempt_timed_out = True
                    step_error = "Zaman aşımı"
                    failed_step = "embed"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "embed", "error": step_error, "is_timeout": True})
                    logger.warning("[%s] deneme %d embed: zaman aşımı", upload_filename, attempt)
                except Exception as exc:
                    step_error = str(exc)
                    failed_step = "embed"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "embed", "error": step_error, "is_timeout": False})
                    logger.error("[%s] deneme %d embed: %s", upload_filename, attempt, exc)

            # ---- write ----
            if failed_step is None:
                yield _sse({"type": "step_start", "filename": upload_filename, "step": "write"})
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(_do_write, output_filename),
                        timeout=STEP_TIMEOUTS["write"],
                    )
                    yield _sse({"type": "step_done", "filename": upload_filename, "step": "write"})
                except asyncio.TimeoutError:
                    attempt_timed_out = True
                    step_error = "Zaman aşımı"
                    failed_step = "write"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "write", "error": step_error, "is_timeout": True})
                    logger.warning("[%s] deneme %d write: zaman aşımı", upload_filename, attempt)
                except Exception as exc:
                    step_error = str(exc)
                    failed_step = "write"
                    yield _sse({"type": "step_error", "filename": upload_filename,
                                "step": "write", "error": step_error, "is_timeout": False})
                    logger.error("[%s] deneme %d write: %s", upload_filename, attempt, exc)

            # ---- end of attempt ----
            if failed_step is None:
                cv_success = True
                yield _sse({"type": "cv_done", "filename": upload_filename, "attempts": attempt})
                logger.info("[%s] Tamamlandı (deneme %d)", upload_filename, attempt)
                success_count += 1
                break
            elif attempt_timed_out and attempt == 1:
                # Timeout on first attempt → grant one retry
                retry = True
                # Loop continues to attempt 2
            else:
                # Non-timeout error OR second attempt failed → skip CV
                yield _sse({"type": "cv_failed", "filename": upload_filename,
                            "failed_step": failed_step, "error": step_error})
                logger.error("[%s] Başarısız (deneme %d, adım: %s). Atlanıyor.",
                             upload_filename, attempt, failed_step)
                failed_count += 1
                break

    yield _sse({
        "type": "complete",
        "total": len(filenames),
        "success": success_count,
        "failed": failed_count,
    })


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

class BulkProcessRequest(BaseModel):
    filenames: list[str]


@router.post("/bulk-process")
async def bulk_process(body: BulkProcessRequest):
    """
    Process a list of already-uploaded CV files through the full pipeline
    (convert → extract → embed → write) with per-step timeouts and automatic
    retry on timeout.  Progress is streamed as Server-Sent Events.
    """
    return StreamingResponse(
        _process_all(body.filenames),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
