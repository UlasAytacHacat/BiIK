from __future__ import annotations

import os
import re

from neo4j import GraphDatabase

from src.base import BaseWriter
from src.schema import GraphData

_DEFAULT_URI = "bolt://localhost:7687"


class MemgraphWriter(BaseWriter):
    def __init__(self):
        uri = os.getenv("MEMGRAPH_URI", _DEFAULT_URI)
        user = os.getenv("MEMGRAPH_USER", "")
        password = os.getenv("MEMGRAPH_PASSWORD", "")
        auth = (user, password) if user else None
        self._driver = GraphDatabase.driver(uri, auth=auth)
        print(f"[SİSTEM] Memgraph bağlantısı: {uri}")

    def write(self, graph_data: GraphData, source_filename: str = "") -> None:
        nodes_ok = nodes_fail = rels_ok = rels_fail = 0

        with self._driver.session() as session:
            for entity in graph_data.entities:
                try:
                    session.execute_write(self._merge_node, entity.id, entity.label, entity.properties)
                    nodes_ok += 1
                except Exception as e:
                    print(f"  [HATA] Node '{entity.id}': {e}")
                    nodes_fail += 1

            for rel in graph_data.relationships:
                try:
                    session.execute_write(self._merge_rel, rel.source, rel.target, rel.type, rel.properties)
                    rels_ok += 1
                except Exception as e:
                    print(f"  [HATA] İlişki '{rel.source}→{rel.target}' ({rel.type}): {e}")
                    rels_fail += 1

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
    # Static transaction functions
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_node(tx, node_id: str, label: str, props: dict) -> None:
        safe_label = re.sub(r"[^A-Za-z0-9_]", "", label)
        clean_props = {k: v for k, v in props.items() if v is not None}
        query = (
            f"MERGE (n:{safe_label} {{id: $id}}) "
            f"SET n += $props"
        )
        tx.run(query, id=node_id, props=clean_props)

    @staticmethod
    def _merge_rel(tx, source: str, target: str, rel_type: str, props: dict) -> None:
        safe_type = re.sub(r"[^A-Z0-9_]", "", rel_type.upper())
        clean_props = {k: v for k, v in props.items() if v is not None}
        query = (
            f"MATCH (s {{id: $source}}), (t {{id: $target}}) "
            f"MERGE (s)-[r:{safe_type}]->(t) "
            f"SET r += $props"
        )
        tx.run(query, source=source, target=target, props=clean_props)
