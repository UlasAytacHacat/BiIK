from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.openai_embedder import OpenAIEmbedder
from src.schema import GraphData

OUTPUT_DIR = Path("output")

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_embedder: OpenAIEmbedder | None = None


def get_embedder() -> OpenAIEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = OpenAIEmbedder()
    return _embedder


def _already_embedded(graph_data: GraphData) -> bool:
    return any(
        len(e.properties.get("embedding", [])) > 0
        for e in graph_data.entities
    )


# ---------------------------------------------------------------------------
# İş mantığı
# ---------------------------------------------------------------------------

async def run_embed(filename: str) -> dict:
    """
    output/{filename} graph JSON'una embedding ekler (in-place).
    Sonucu {"filename": filename, "cached": bool, "status": "embedded"} döner.
    """
    src = OUTPUT_DIR / filename
    if not src.exists():
        raise FileNotFoundError(f"'{filename}' output/ klasöründe bulunamadı.")

    graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))

    if _already_embedded(graph_data):
        return {"filename": filename, "cached": True, "status": "embedded"}

    embedder = get_embedder()
    graph_data = await asyncio.to_thread(embedder.embed, graph_data)

    src.write_text(
        json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"filename": filename, "cached": False, "status": "embedded"}


# ---------------------------------------------------------------------------
# FastAPI endpoint — geriye dönük uyumluluk için korunur
# ---------------------------------------------------------------------------

class EmbedRequest(BaseModel):
    filename: str


@router.post("/embed")
async def embed(body: EmbedRequest):
    try:
        return await run_embed(body.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding başarısız: {e}")
