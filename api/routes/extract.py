from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.groq_extractor import GroqExtractor
from src.schema import GraphData

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_extractor: GroqExtractor | None = None


def get_extractor() -> GroqExtractor:
    global _extractor
    if _extractor is None:
        _extractor = GroqExtractor()
    return _extractor


# ---------------------------------------------------------------------------
# Rate limit hata sınıfı — pipeline_runner tarafından yakalanır
# ---------------------------------------------------------------------------

class RateLimitError(Exception):
    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit — {retry_after}s bekle")


# ---------------------------------------------------------------------------
# İş mantığı — pipeline_runner ve endpoint tarafından ortak kullanılır
# ---------------------------------------------------------------------------

async def run_extract(filename: str) -> dict:
    """
    data/{filename} → output/{stem}_graph.json extraction yapar.
    Sonucu {"filename": output_filename, "cached": bool, "status": "extracted"} döner.
    429 hatasında RateLimitError, diğer hatalarda Exception fırlatır.
    """
    src = DATA_DIR / filename
    if not src.exists():
        raise FileNotFoundError(f"'{filename}' data/ klasöründe bulunamadı.")

    stem = Path(filename).stem
    output_path = OUTPUT_DIR / f"{stem}_graph.json"

    if output_path.exists():
        return {"filename": output_path.name, "cached": True, "status": "extracted"}

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("text", "")
    if not text.strip():
        raise ValueError("CV metni boş.")

    try:
        extractor = get_extractor()
        graph_data: GraphData = await asyncio.to_thread(
            extractor.extract, text, data.get("annotations", [])
        )
    except Exception as exc:
        exc_str = str(exc)
        if "429" in exc_str:
            match = re.search(r"try again in\s+([\d.]+)s", exc_str)
            retry_after = float(match.group(1)) + 5 if match else 60.0
            raise RateLimitError(retry_after=retry_after) from exc
        raise

    output_path.write_text(
        json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"filename": output_path.name, "cached": False, "status": "extracted"}


# ---------------------------------------------------------------------------
# FastAPI endpoint — geriye dönük uyumluluk için korunur
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    filename: str


@router.post("/extract")
async def extract(body: ExtractRequest):
    try:
        return await run_extract(body.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limit: {e.retry_after}s bekle")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Extraction başarısız: {e}")
