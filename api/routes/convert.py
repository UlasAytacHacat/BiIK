from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import fitz  # pymupdf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

UPLOADS_DIR = Path("uploads")
DATA_DIR = Path("data")

router = APIRouter()


async def run_convert(filename: str) -> dict:
    """
    uploads/{filename} → data/{stem}.json dönüşümünü yapar.
    Sonucu {"filename": data_filename, "cached": bool, "status": "converted"} olarak döner.
    Hata durumunda exception fırlatır.
    """
    src = UPLOADS_DIR / filename
    if not src.exists():
        raise FileNotFoundError(f"'{filename}' uploads/ klasöründe bulunamadı.")

    stem = src.stem
    suffix = src.suffix.lower()

    if suffix == ".json":
        dest = DATA_DIR / src.name
        if dest.exists():
            return {"filename": src.name, "cached": True, "status": "converted"}
        await asyncio.to_thread(shutil.copy2, str(src), str(dest))
        return {"filename": src.name, "cached": False, "status": "converted"}

    if suffix == ".pdf":
        dest_name = f"{stem}.json"
        dest = DATA_DIR / dest_name
        if dest.exists():
            return {"filename": dest_name, "cached": True, "status": "converted"}

        def _convert_pdf():
            doc = fitz.open(str(src))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            dest.write_text(
                json.dumps({"text": text, "annotations": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            return dest_name

        await asyncio.to_thread(_convert_pdf)
        return {"filename": dest_name, "cached": False, "status": "converted"}

    raise ValueError(f"Desteklenmeyen dosya türü: '{suffix}'.")


# ---------------------------------------------------------------------------
# FastAPI endpoint — geriye dönük uyumluluk için korunur
# ---------------------------------------------------------------------------

class ConvertRequest(BaseModel):
    filename: str


@router.post("/convert")
async def convert(body: ConvertRequest):
    try:
        return await run_convert(body.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dönüştürme başarısız: {e}")
