from __future__ import annotations

import logging

from src.labels import VECTOR_INDEX_LABELS
from src.node2vec_config import DEFAULT_CONFIG, Node2VecConfig

logger = logging.getLogger(__name__)


class Node2VecRunner:
    def __init__(self, session_factory, config: Node2VecConfig = DEFAULT_CONFIG):
        self._session_factory = session_factory  # callable → Session
        self._config = config

    def run(self) -> dict:
        """
        Tüm graph üzerinde Node2Vec çalıştırır.
        Her node'a config.embedding_property adında vektör yazar.
        """
        cfg = self._config
        with self._session_factory() as session:
            result = session.run(
                "CALL node2vec.set_embeddings("
                "$directed, $p, $q, $num_walks, $walk_length, $vector_size"
                ") YIELD *",
                directed=cfg.directed,
                p=cfg.p,
                q=cfg.q,
                num_walks=cfg.num_walks,
                walk_length=cfg.walk_length,
                vector_size=cfg.vector_size,
            )
            records = list(result)
            nodes_updated = len(records)

        logger.info(f"Node2Vec tamamlandı: {nodes_updated} node güncellendi")
        return {
            "nodes_updated": nodes_updated,
            "config_used": {
                "directed": cfg.directed,
                "p": cfg.p,
                "q": cfg.q,
                "num_walks": cfg.num_walks,
                "walk_length": cfg.walk_length,
                "vector_size": cfg.vector_size,
                "embedding_property": cfg.embedding_property,
            },
        }

    def verify(self) -> dict:
        """
        Node2Vec embedding'lerinin kaç node'a yazıldığını kontrol eder.
        Sonuç: {label: count} — her label için embedding olan node sayısı.
        """
        counts = {}
        prop = self._config.embedding_property
        with self._session_factory() as session:
            for label in VECTOR_INDEX_LABELS:
                result = session.run(
                    f"MATCH (n:{label}) WHERE n[$prop] IS NOT NULL RETURN count(n) AS c",
                    prop=prop,
                )
                counts[label] = result.single()["c"]
        return counts
