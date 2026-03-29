from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.groq_extractor import GroqExtractor
from src.schema import GraphData

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton — inter-request delay ve bağlantı yeniden kullanımı için
# ---------------------------------------------------------------------------
_extractor: GroqExtractor | None = None


def get_extractor() -> GroqExtractor:
    global _extractor
    if _extractor is None:
        _extractor = GroqExtractor()
    return _extractor


class ExtractRequest(BaseModel):
    filename: str


@router.post("/extract")
def extract(body: ExtractRequest):
    src = DATA_DIR / body.filename
    if not src.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{body.filename}' data/ klasöründe bulunamadı.",
        )

    stem = Path(body.filename).stem
    output_path = OUTPUT_DIR / f"{stem}_graph.json"

    if output_path.exists():
        return {"filename": output_path.name, "cached": True, "status": "extracted"}

    try:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"JSON okunamadı: {e}")

    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=422, detail="CV metni boş.")

    try:
        extractor = get_extractor()
        graph_data: GraphData = extractor.extract(text, data.get("annotations", []))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Extraction başarısız: {e}")

    try:
        output_path.write_text(
            json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sonuç kaydedilemedi: {e}")

    return {"filename": output_path.name, "cached": False, "status": "extracted"}
