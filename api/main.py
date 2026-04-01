from __future__ import annotations

import logging
import logging.config
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import candidates, convert, embed, extract, ingest, process, reindex, write

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — writes to logs/process.log and stdout
# ---------------------------------------------------------------------------
Path("logs").mkdir(exist_ok=True)
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/process.log",
            "encoding": "utf-8",
            "formatter": "default",
        },
    },
    "root": {"level": "INFO", "handlers": ["console", "file"]},
})

# ---------------------------------------------------------------------------
# Startup: gerekli klasörleri oluştur
# ---------------------------------------------------------------------------
for _dir in ("uploads", "data", "output"):
    Path(_dir).mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="BiIK API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router, tags=["candidates"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(convert.router, tags=["convert"])
app.include_router(extract.router, tags=["extract"])
app.include_router(embed.router, tags=["embed"])
app.include_router(write.router, tags=["write"])
app.include_router(reindex.router, tags=["reindex"])
app.include_router(process.router, tags=["process"])


if __name__ == "__main__":
    import sys
    import uvicorn

    # backend/ klasöründen `python api/main.py` ile çalıştırılabilmesi için
    sys.path.insert(0, str(Path(__file__).parent.parent))
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
