"""
Tüm CV'leri baştan işler: convert → extract → embed → write
Çalıştırma: python reprocess_all.py
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Pipeline adımları (process.py'den alındı)
# ---------------------------------------------------------------------------

def do_convert(upload_filename: str) -> str:
    import fitz
    src = UPLOADS_DIR / upload_filename
    stem = src.stem
    suffix = src.suffix.lower()

    if suffix == ".json":
        dest = DATA_DIR / src.name
        shutil.copy2(src, dest)
        return src.name

    if suffix == ".pdf":
        doc = fitz.open(str(src))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        dest_name = f"{stem}.json"
        (DATA_DIR / dest_name).write_text(
            json.dumps({"text": text, "annotations": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        return dest_name

    raise ValueError(f"Desteklenmeyen dosya türü: '{suffix}'")


def do_extract(data_filename: str, extractor) -> str:
    src = DATA_DIR / data_filename
    stem = Path(data_filename).stem
    output_path = OUTPUT_DIR / f"{stem}_graph.json"

    if output_path.exists():
        logger.info("  [extract] Atlandı (zaten var): %s", output_path.name)
        return output_path.name

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    text = data.get("text", "")
    if not text.strip():
        raise ValueError("CV metni boş.")

    graph_data = extractor.extract(text, data.get("annotations", []))
    output_path.write_text(
        json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path.name


def do_embed(output_filename: str, embedder) -> None:
    from api.routes.embed import _already_embedded
    from src.schema import GraphData

    src = OUTPUT_DIR / output_filename
    graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))

    if _already_embedded(graph_data):
        logger.info("  [embed] Atlandı (zaten embed edilmiş)")
        return

    graph_data = embedder.embed(graph_data)
    src.write_text(
        json.dumps(graph_data.model_dump(), indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


def do_write(output_filename: str, writer) -> None:
    from src.schema import GraphData

    src = OUTPUT_DIR / output_filename
    sentinel = OUTPUT_DIR / (Path(output_filename).stem + ".written")

    if sentinel.exists():
        logger.info("  [write] Atlandı (sentinel var)")
        return

    graph_data = GraphData.model_validate_json(src.read_text(encoding="utf-8"))
    writer.write(graph_data, output_filename)
    sentinel.touch()


# ---------------------------------------------------------------------------
# Ana döngü
# ---------------------------------------------------------------------------

def main():
    from src.groq_extractor import GroqExtractor
    from src.openai_embedder import OpenAIEmbedder
    from src.memgraph_writer import MemgraphWriter

    logger.info("Extractor, Embedder, Writer başlatılıyor...")
    extractor = GroqExtractor()
    embedder = OpenAIEmbedder()
    writer = MemgraphWriter()
    logger.info("Hazır.")

    filenames = sorted(UPLOADS_DIR.iterdir(), key=lambda p: p.name)
    filenames = [f.name for f in filenames if f.suffix.lower() in (".pdf", ".json")]

    total = len(filenames)
    success = 0
    failed = 0

    for i, upload_filename in enumerate(filenames, 1):
        logger.info("[%d/%d] %s", i, total, upload_filename)

        try:
            # convert
            data_filename = do_convert(upload_filename)
            logger.info("  [convert] OK → %s", data_filename)

            # extract
            output_filename = do_extract(data_filename, extractor)
            logger.info("  [extract] OK → %s", output_filename)

            # embed
            do_embed(output_filename, embedder)
            logger.info("  [embed] OK")

            # write
            do_write(output_filename, writer)
            logger.info("  [write] OK")

            success += 1

        except Exception as exc:
            logger.error("  HATA: %s — atlanıyor.", exc)
            failed += 1
            time.sleep(2)

    writer.close()
    logger.info("Tamamlandı. Başarılı: %d / %d, Hatalı: %d", success, total, failed)


if __name__ == "__main__":
    main()
