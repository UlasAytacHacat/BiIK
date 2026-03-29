from __future__ import annotations

import os
import time

from openai import OpenAI

from src.base import BaseEmbedder
from src.schema import GraphData

_EMBED_LABELS = {"Yetenek", "Pozisyon", "Proje", "Sirket"}
_MODEL = "text-embedding-3-large"


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print(f"[SİSTEM] OpenAI Embedding Modu Aktif ({_MODEL})...")

    def embed(self, graph_data: GraphData) -> GraphData:
        for entity in graph_data.entities:
            if entity.label not in _EMBED_LABELS:
                continue

            props = entity.properties
            if entity.label == "Proje":
                text = props.get("name", "") + " " + props.get("aciklama", "")
            else:
                text = props.get("name", "")

            text = text.strip()
            if not text:
                continue

            response = self.client.embeddings.create(model=_MODEL, input=text)
            entity.properties["embedding"] = response.data[0].embedding
            time.sleep(0.1)

        return graph_data
