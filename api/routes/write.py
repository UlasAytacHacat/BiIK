from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.memgraph_writer import MemgraphWriter
from src.schema import GraphData

OUTPUT_DIR = Path("output")

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_writer: MemgraphWriter | None = None


def get_writer() -> MemgraphWriter:
    global _writer
    if _writer is None:
        _writer = MemgraphWriter()
    return _writer


# ---------------------------------------------------------------------------
# İş mantığı
# ---------------------------------------------------------------------------

async def run_write(filename: str) -> dict:
    """
    output/{filename} graph JSON'unu Memgraph'a yazar.
    Başarıda sentinel dosyası oluşturur.
    Sonucu {"filename": filename, "cached": bool, "status": ...} döner.
    """
    src = OUTPUT_DIR / filename
    if not src.exists():
        raise FileNotFoundError(f"'{filename}' output/ klasöründe bulunamadı.")

    sentinel = OUTPUT_DIR / (Path(filename).stem + ".written")
    if sentinel.exists():
        return {"filename": filename, "cached": True, "status": "already_written"}

    graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))

    writer = get_writer()
    await asyncio.to_thread(writer.write, graph_data, filename)
    sentinel.touch()

    return {
        "filename": filename,
        "cached": False,
        "nodes_written": len(graph_data.entities),
        "rels_written": len(graph_data.relationships),
        "status": "written",
    }


# ---------------------------------------------------------------------------
# FastAPI endpoint — geriye dönük uyumluluk için korunur
# ---------------------------------------------------------------------------

class WriteRequest(BaseModel):
    filename: str


@router.post("/write")
async def write(body: WriteRequest):
    try:
        return await run_write(body.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Memgraph yazma başarısız: {e}")
