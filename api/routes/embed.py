from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.openai_embedder import OpenAIEmbedder
from src.schema import GraphData

OUTPUT_DIR = Path("output")

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton — OpenAI client bağlantısı yeniden kullanımı için
# ---------------------------------------------------------------------------
_embedder: OpenAIEmbedder | None = None


def get_embedder() -> OpenAIEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = OpenAIEmbedder()
    return _embedder


class EmbedRequest(BaseModel):
    filename: str


def _already_embedded(graph_data: GraphData) -> bool:
    return any(
        len(e.properties.get("embedding", [])) > 0
        for e in graph_data.entities
    )


@router.post("/embed")
def embed(body: EmbedRequest):
    src = OUTPUT_DIR / body.filename
    if not src.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{body.filename}' output/ klasöründe bulunamadı.",
        )

    try:
        graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Graph JSON okunamadı: {e}")

    if _already_embedded(graph_data):
        return {"filename": body.filename, "cached": True, "status": "embedded"}

    try:
        embedder = get_embedder()
        graph_data = embedder.embed(graph_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding başarısız: {e}")

    try:
        src.write_text(
            json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sonuç kaydedilemedi: {e}")

    return {"filename": body.filename, "cached": False, "status": "embedded"}
