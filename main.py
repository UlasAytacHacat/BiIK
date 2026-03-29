import json
from pathlib import Path

from dotenv import load_dotenv

from src.groq_extractor import GroqExtractor
from src.openai_embedder import OpenAIEmbedder
from src.pipeline import CVPipeline

load_dotenv()


def test_single_cv():
    data_dir = Path("data")
    first_cv = sorted(data_dir.glob("*.json"))[15]  # Rastgele bir CV seçelim
    print(f"[TEST] {first_cv.name} işleniyor...\n")

    with open(first_cv, encoding="utf-8") as f:
        data = json.load(f)

    extractor = GroqExtractor()
    graph_data = extractor.extract(data.get("text", ""), data.get("annotations", []))

    embedder = OpenAIEmbedder()
    graph_data = embedder.embed(graph_data)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{first_cv.stem}_graph.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_data.model_dump(), f, indent=4, ensure_ascii=False)
    print(f"[KAYIT] {output_path}")


def run_pipeline():
    pipeline = CVPipeline(extractor=GroqExtractor(), embedder=OpenAIEmbedder())
    pipeline.run_all()


if __name__ == "__main__":
    test_single_cv()
    # run_pipeline()
