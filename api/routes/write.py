from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.memgraph_writer import MemgraphWriter
from src.schema import GraphData

OUTPUT_DIR = Path("output")

router = APIRouter()


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

    try:
        graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Graph JSON okunamadı: {e}")

    try:
        with MemgraphWriter() as writer:
            writer.write(graph_data, body.filename)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Memgraph yazma başarısız: {e}")

    (OUTPUT_DIR / (Path(body.filename).stem + ".written")).touch()

    return {
        "filename": body.filename,
        "nodes_written": len(graph_data.entities),
        "rels_written": len(graph_data.relationships),
        "status": "written",
    }
