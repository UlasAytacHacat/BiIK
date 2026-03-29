from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.base import BaseEmbedder, BaseExtractor, BaseWriter
from src.schema import GraphData


# ---------------------------------------------------------------------------
# Veri sınıfı: tek bir CV'nin işlem sonucu
# ---------------------------------------------------------------------------
@dataclass
class StepResult:
    filename: str
    success: bool
    error: str = ""


# ---------------------------------------------------------------------------
# Varsayılan Writer: JSON dosyasına yazar
# Aşama 4'te MemgraphWriter(BaseWriter) ile değiştirilebilir.
# ---------------------------------------------------------------------------
class JSONWriter(BaseWriter):
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def write(self, graph_data: GraphData, source_filename: str) -> None:
        stem = Path(source_filename).stem
        output_path = self.output_dir / f"{stem}_graph.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph_data.model_dump(), f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Placeholder Embedder: veriyi değiştirmeden geçirir.
# Aşama 3'te OpenAIEmbedder(BaseEmbedder) ile değiştirilebilir.
# ---------------------------------------------------------------------------
class MultiWriter(BaseWriter):
    """Birden fazla writer'a sırayla yazar."""

    def __init__(self, *writers: BaseWriter):
        self._writers = writers

    def write(self, graph_data: GraphData, source_filename: str) -> None:
        for w in self._writers:
            w.write(graph_data, source_filename)


class PassThroughEmbedder(BaseEmbedder):
    def embed(self, graph_data: GraphData) -> GraphData:
        return graph_data


# ---------------------------------------------------------------------------
# Pipeline: extract → embed → write adımlarını sırayla çalıştırır.
# Bağımlılıklar dışarıdan enjekte edilir — somut sınıflara bağımlılık yok.
# ---------------------------------------------------------------------------
class CVPipeline:
    def __init__(
        self,
        extractor: BaseExtractor,
        embedder: BaseEmbedder | None = None,
        writer: BaseWriter | None = None,
        data_dir: str = "data",
    ):
        self.extractor = extractor
        self.embedder = embedder or PassThroughEmbedder()
        self.writer = writer or JSONWriter()
        self.data_dir = Path(data_dir)

    def run_all(self) -> list[StepResult]:
        cv_files = sorted(self.data_dir.glob("*.json"))
        if not cv_files:
            print(f"(!) '{self.data_dir}' klasöründe JSON bulunamadı.")
            return []

        print(f"--- Toplam {len(cv_files)} dosya işleniyor ---")
        results = [self._process(f) for f in cv_files]

        success_count = sum(1 for r in results if r.success)
        failed = [r for r in results if not r.success]

        print(f"\n--- {success_count}/{len(results)} başarıyla tamamlandı ---")
        for r in failed:
            print(f"  [HATA] {r.filename}: {r.error}")

        return results

    # ------------------------------------------------------------------
    # Tek CV: load → extract → embed → write
    # ------------------------------------------------------------------
    def _process(self, filepath: Path) -> StepResult:
        print(f"\n[İŞLENİYOR] {filepath.name}...")
        try:
            text, annotations = self._load(filepath)

            if not text.strip():
                print("  [UYARI] Metin boş, atlanıyor.")
                return StepResult(filename=filepath.name, success=False, error="Boş metin")

            graph_data = self.extractor.extract(text, annotations)  # Aşama 2'de LLMExtractor
            graph_data = self.embedder.embed(graph_data)            # Aşama 3'te OpenAIEmbedder
            self.writer.write(graph_data, filepath.name)            # Aşama 4'te MemgraphWriter

            print("  [TAMAM]")
            return StepResult(filename=filepath.name, success=True)

        except Exception as e:
            print(f"  [HATA] {e}")
            return StepResult(filename=filepath.name, success=False, error=str(e))

    def _load(self, filepath: Path) -> tuple[str, list]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("text", ""), data.get("annotations", [])
