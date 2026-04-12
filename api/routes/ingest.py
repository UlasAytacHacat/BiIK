from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".pdf", ".json"}

router = APIRouter()


async def save_upload(file: UploadFile, job_id: str) -> str:
    """
    Dosyayı uploads/ altına {job_id[:8]}_{original_filename} adıyla kaydeder.
    Desteklenmeyen uzantıda ValueError fırlatır.
    Kaydedilen dosya adını döner.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Desteklenmeyen dosya türü: '{suffix}'. Kabul edilenler: .pdf, .json"
        )
    prefixed_name = f"{job_id[:8]}_{file.filename}"
    dest = UPLOADS_DIR / prefixed_name
    content = await file.read()
    dest.write_bytes(content)
    return prefixed_name


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """Tekli dosya yükleme — geriye dönük uyumluluk için korunur."""
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
