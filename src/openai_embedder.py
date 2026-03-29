from __future__ import annotations

import os
import time

from openai import OpenAI

from src.base import BaseEmbedder
from src.schema import GraphData

_EMBED_LABELS = {"Yetenek", "Sirket", "Pozisyon", "Egitim", "Proje"}
_MODEL = "text-embedding-3-large"


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print(f"[SİSTEM] OpenAI Embedding Modu Aktif ({_MODEL})...")

    def embed(self, graph_data: GraphData) -> GraphData:
        embedded = 0
        skipped_label = 0
        skipped_empty = 0

        for entity in graph_data.entities:
            if entity.label not in _EMBED_LABELS:
                skipped_label += 1
                continue

            props = entity.properties
            if entity.label == "Proje":
                text = props.get("name", "") + " " + props.get("aciklama", "")
            elif entity.label == "Yetenek" and not props.get("name"):
                # ID'den türet: skill_machine_learning → Machine Learning
                text = entity.id.split("_", 1)[-1].replace("_", " ").title()
            else:
                text = props.get("name", "")

            text = text.strip()
            if not text:
                print(f"  [WARN] '{entity.id}' için name türetilemedi, atlanıyor.")
                skipped_empty += 1
                continue

            response = self.client.embeddings.create(model=_MODEL, input=text)
            entity.properties["embedding"] = response.data[0].embedding
            embedded += 1
            time.sleep(0.1)

        print(f"  [EMBED] {embedded} embed edildi | {skipped_label} label dışı atlandı | {skipped_empty} boş name atlandı")
        return graph_data
