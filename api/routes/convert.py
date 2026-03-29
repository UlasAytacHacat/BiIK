from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz  # pymupdf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

UPLOADS_DIR = Path("uploads")
DATA_DIR = Path("data")

router = APIRouter()


class ConvertRequest(BaseModel):
    filename: str


@router.post("/convert")
def convert(body: ConvertRequest):
    src = UPLOADS_DIR / body.filename
    if not src.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{body.filename}' uploads/ klasöründe bulunamadı.",
        )

    suffix = src.suffix.lower()
    stem = src.stem

    if suffix == ".json":
        dest = DATA_DIR / src.name
        try:
            shutil.copy2(src, dest)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Kopyalama başarısız: {e}")
        return {"filename": src.name, "status": "converted"}

    if suffix == ".pdf":
        try:
            doc = fitz.open(str(src))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF okunamadı: {e}")

        dest_name = f"{stem}.json"
        dest = DATA_DIR / dest_name
        try:
            dest.write_text(
                json.dumps({"text": text, "annotations": []}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"JSON yazılamadı: {e}")

        return {"filename": dest_name, "status": "converted"}

    raise HTTPException(
        status_code=422,
        detail=f"Desteklenmeyen dosya türü: '{suffix}'.",
    )
