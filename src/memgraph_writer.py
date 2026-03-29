from __future__ import annotations

import os
import re
from collections import defaultdict

from neo4j import GraphDatabase

from src.base import BaseWriter
from src.schema import GraphData

_DEFAULT_URI = "bolt://localhost:7687"

_EMBEDDABLE_LABELS = {"Yetenek", "Pozisyon", "Proje", "Sirket"}
_EMBEDDING_DIM = 3072


class MemgraphWriter(BaseWriter):
    def __init__(self):
        uri = os.getenv("MEMGRAPH_URI", _DEFAULT_URI)
        user = os.getenv("MEMGRAPH_USER", "")
        password = os.getenv("MEMGRAPH_PASSWORD", "")
        auth = (user, password) if user else None
        self._driver = GraphDatabase.driver(uri, auth=auth)
        print(f"[SİSTEM] Memgraph bağlantısı: {uri}")

    def write(self, graph_data: GraphData, source_filename: str = "") -> None:
        self._ensure_vector_indexes()

        with self._driver.session() as session:
            nodes_ok, nodes_fail = session.execute_write(
                self._batch_merge_nodes, graph_data.entities
            )
            rels_ok, rels_fail = session.execute_write(
                self._batch_merge_rels, graph_data.relationships
            )

        print(
            f"  [MEMGRAPH] {nodes_ok} node yazıldı, {nodes_fail} başarısız | "
            f"{rels_ok} ilişki yazıldı, {rels_fail} başarısız"
        )

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> MemgraphWriter:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Vector index
    # ------------------------------------------------------------------

    def _ensure_vector_indexes(self) -> None:
        with self._driver.session() as session:
            for label in _EMBEDDABLE_LABELS:
                idx_name = f"idx_{label.lower()}_embedding"
                try:
                    session.run(
                        "CALL vector_search.create_index($name, $dim, $label, $prop, $metric) YIELD *",
                        name=idx_name,
                        dim=_EMBEDDING_DIM,
                        label=label,
                        prop="embedding",
                        metric="cos",
                    )
                    print(f"  [INDEX] {idx_name} oluşturuldu")
                except Exception:
                    pass  # zaten varsa sessizce geç

    # ------------------------------------------------------------------
    # Batch transaction functions
    # ------------------------------------------------------------------

    @staticmethod
    def _batch_merge_nodes(tx, entities) -> tuple[int, int]:
        nodes_by_label: dict[str, list[dict]] = defaultdict(list)
        for e in entities:
            clean_props = {k: v for k, v in e.properties.items() if v is not None}
            nodes_by_label[e.label].append({"id": e.id, "props": clean_props})

        ok = fail = 0
        for label, node_list in nodes_by_label.items():
            safe_label = re.sub(r"[^A-Za-z0-9_]", "", label)
            query = (
                f"UNWIND $nodes AS node "
                f"MERGE (n:{safe_label} {{id: node.id}}) "
                f"SET n += node.props"
            )
            try:
                tx.run(query, nodes=node_list)
                ok += len(node_list)
            except Exception as e:
                print(f"  [HATA] Batch node ({label}): {e}")
                fail += len(node_list)

        return ok, fail

    @staticmethod
    def _batch_merge_rels(tx, relationships) -> tuple[int, int]:
        rels_by_type: dict[str, list[dict]] = defaultdict(list)
        for r in relationships:
            clean_props = {k: v for k, v in r.properties.items() if v is not None}
            rels_by_type[r.type].append(
                {"source": r.source, "target": r.target, "props": clean_props}
            )

        ok = fail = 0
        for rel_type, rel_list in rels_by_type.items():
            safe_type = re.sub(r"[^A-Z0-9_]", "", rel_type.upper())
            query = (
                f"UNWIND $rels AS rel "
                f"MATCH (s {{id: rel.source}}), (t {{id: rel.target}}) "
                f"MERGE (s)-[r:{safe_type}]->(t) "
                f"SET r += rel.props"
            )
            try:
                tx.run(query, rels=rel_list)
                ok += len(rel_list)
            except Exception as e:
                print(f"  [HATA] Batch rel ({rel_type}): {e}")
                fail += len(rel_list)

        return ok, fail
