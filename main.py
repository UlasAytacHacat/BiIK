import json
from pathlib import Path

from dotenv import load_dotenv

from src.groq_extractor import GroqExtractor
from src.memgraph_writer import MemgraphWriter
from src.openai_embedder import OpenAIEmbedder
from src.pipeline import CVPipeline, JSONWriter, MultiWriter

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


def test_memgraph_connection():
    with MemgraphWriter() as writer:
        with writer._driver.session() as session:
            result = session.run("RETURN 1 AS test")
            record = result.single()
            print(f"[BAĞLANTI] Memgraph yanıtı: {record['test']}")


def run_pipeline():
    with MemgraphWriter() as writer:
        pipeline = CVPipeline(
            extractor=GroqExtractor(),
            embedder=OpenAIEmbedder(),
            writer=MultiWriter(JSONWriter(), writer),
        )
        pipeline.run_all()


if __name__ == "__main__":
    test_single_cv()
    # run_pipeline()
