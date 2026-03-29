from abc import ABC, abstractmethod
from src.schema import GraphData


class BaseExtractor(ABC):
    """
    CV metninden GraphData üretmekten sorumlu sözleşme.
    Kural tabanlı, LLM tabanlı veya hibrit implementasyonlar bu sınıftan türer.
    """

    @abstractmethod
    def extract(self, text: str, annotations: list) -> GraphData:
        ...


class BaseEmbedder(ABC):
    """
    GraphData içindeki entity'lere vektör eklemekten sorumlu sözleşme.
    Aşama 3'te OpenAI Embeddings implementasyonu bu sınıftan türeyecek.
    """

    @abstractmethod
    def embed(self, graph_data: GraphData) -> GraphData:
        ...


class BaseWriter(ABC):
    """
    GraphData'yı bir hedefe (JSON dosyası, Memgraph vb.) yazmaktan sorumlu sözleşme.
    """

    @abstractmethod
    def write(self, graph_data: GraphData, source_filename: str) -> None:
        ...
