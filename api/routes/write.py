from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.memgraph_writer import MemgraphWriter
from src.schema import GraphData

OUTPUT_DIR = Path("output")

router = APIRouter()

# ---------------------------------------------------------------------------
# Singleton — Memgraph driver bağlantısı yeniden kullanımı için
# ---------------------------------------------------------------------------
_writer: MemgraphWriter | None = None


def get_writer() -> MemgraphWriter:
    global _writer
    if _writer is None:
        _writer = MemgraphWriter()
    return _writer


class WriteRequest(BaseModel):
    filename: str


@router.post("/write")
def write(body: WriteRequest):
    src = OUTPUT_DIR / body.filename
    if not src.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{body.filename}' output/ klasöründe bulunamadı.",
        )

    sentinel = OUTPUT_DIR / (Path(body.filename).stem + ".written")
    if sentinel.exists():
        return {"filename": body.filename, "cached": True, "status": "already_written"}

    try:
        graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Graph JSON okunamadı: {e}")

    try:
        writer = get_writer()
        writer.write(graph_data, body.filename)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Memgraph yazma başarısız: {e}")

    sentinel.touch()

    return {
        "filename": body.filename,
        "nodes_written": len(graph_data.entities),
        "rels_written": len(graph_data.relationships),
        "status": "written",
    }
