from __future__ import annotations

# ---------------------------------------------------------------------------
# Node label sabitleri
# ---------------------------------------------------------------------------
NODE_ADAY = "Aday"
NODE_YETENEK = "Yetenek"
NODE_SIRKET = "Sirket"
NODE_POZISYON = "Pozisyon"
NODE_EGITIM = "Egitim"
NODE_SERTIFIKA = "Sertifika"
NODE_PROJE = "Proje"

ALL_NODE_LABELS = {
    NODE_ADAY,
    NODE_YETENEK,
    NODE_SIRKET,
    NODE_POZISYON,
    NODE_EGITIM,
    NODE_SERTIFIKA,
    NODE_PROJE,
}

# ---------------------------------------------------------------------------
# Relation type sabitleri
# ---------------------------------------------------------------------------
REL_SAHIP = "SAHIP"
REL_CALISTI = "CALISTI"
REL_POZISYONUNDA = "POZISYONUNDA"
REL_MEZUN = "MEZUN"
REL_TAMAMLADI = "TAMAMLADI"
REL_PROJEDE_YER_ALDI = "PROJEDE_YER_ALDI"
REL_KULLANDI = "KULLANDI"

ALL_REL_TYPES = {
    REL_SAHIP,
    REL_CALISTI,
    REL_POZISYONUNDA,
    REL_MEZUN,
    REL_TAMAMLADI,
    REL_PROJEDE_YER_ALDI,
    REL_KULLANDI,
}

# ---------------------------------------------------------------------------
# Embedding label'ları — openai_embedder ve memgraph_writer ortak kaynağı
# ---------------------------------------------------------------------------
EMBEDDABLE_LABELS = {
    NODE_YETENEK,
    NODE_SIRKET,
    NODE_POZISYON,
    NODE_EGITIM,
    NODE_PROJE,
}

# Memgraph'ta vector index açılacak label'lar (EMBEDDABLE_LABELS ile aynı)
VECTOR_INDEX_LABELS = EMBEDDABLE_LABELS
