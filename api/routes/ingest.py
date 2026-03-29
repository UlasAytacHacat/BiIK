from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".pdf", ".json"}

router = APIRouter()


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Desteklenmeyen dosya türü: '{suffix}'. Kabul edilenler: .pdf, .json",
        )

    dest = UPLOADS_DIR / file.filename
    try:
        content = await file.read()
        dest.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya kaydedilemedi: {e}")

    return {"filename": file.filename, "status": "uploaded"}
