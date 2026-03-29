import json
from pathlib import Path

from dotenv import load_dotenv

from src.gemini_extractor import GeminiExtractor
from src.pipeline import CVPipeline

load_dotenv()


def test_single_cv():
    data_dir = Path("data")
    first_cv = sorted(data_dir.glob("*.json"))[0]
    print(f"[TEST] {first_cv.name} işleniyor...\n")

    with open(first_cv, encoding="utf-8") as f:
        data = json.load(f)

    extractor = GeminiExtractor()
    graph_data = extractor.extract(data.get("text", ""), data.get("annotations", []))
    print(json.dumps(graph_data.model_dump(), indent=2, ensure_ascii=False))


def run_pipeline():
    pipeline = CVPipeline(extractor=GeminiExtractor())
    pipeline.run_all()


if __name__ == "__main__":
    # test_single_cv()
    run_pipeline()
