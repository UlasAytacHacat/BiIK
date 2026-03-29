# BiIK — Proje Standartları ve Geliştirme Rehberi

## Proje Özeti

BiIK, Türkçe HR ekipleri için CV'lerden knowledge graph üreten ve GraphRAG tabanlı aday öneri sistemi kuran bir Python pipeline'ıdır.

**Teknoloji yığını:** Python 3.10+ · Pydantic v2 · Gemini API · Memgraph · LangGraph  
**Geliştirme ortamı:** Windows, VS Code + Claude Code

---

## Klasör Yapısı

```
BiIK/
├── data/                  # Ham annotated JSON'lar (30 CV)
├── output/                # İşlenmiş graph JSON'lar
├── src/
│   ├── base.py            # Abstract sınıflar (BaseExtractor, BaseEmbedder, BaseWriter)
│   ├── schema.py          # Pydantic modelleri (Entity, Relationship, GraphData)
│   ├── labels.py          # Node label ve relation tip sabitleri
│   ├── pipeline.py        # CVPipeline, JSONWriter, PassThroughEmbedder
│   ├── gemini_extractor.py # LLM extraction (Aşama 2 — aktif)
│   ├── gemini_embedder.py  # Embedding (Aşama 3 — yapılacak)
│   └── memgraph_writer.py  # Graph DB yazıcı (Aşama 4 — yapılacak)
├── prompts/
│   └── tr.py              # Türkçe sistem promptları
├── main.py
├── requirements.txt
├── .env                   # API key'ler (git'e gitmesin)
├── .gitignore
└── CLAUDE.md              # Bu dosya
```

---

## Şema Standartları

### Node Tipleri (label field — tam olarak bu 7 değerden biri)

| Label | Türkçe | Zorunlu Properties |
|-------|--------|-------------------|
| `Aday` | Aday | `name` |
| `Yetenek` | Skill | `name` |
| `Sirket` | Şirket | `name` |
| `Pozisyon` | Pozisyon | `name` |
| `Egitim` | Eğitim | `derece`, `kurum?`, `yil?` |
| `Sertifika` | Sertifika | `name`, `yil?` |
| `Proje` | Proje | `name`, `aciklama?` |

### Relation Tipleri ve Yönleri (tam olarak bu 7 tip)

| Tip | Source | Target | Properties |
|-----|--------|--------|------------|
| `SAHIP` | Aday | Yetenek | `seviye?`, `sure_yil?` |
| `CALISTI` | Aday | Sirket | `rol?`, `baslangic?`, `bitis?` |
| `POZISYONUNDA` | Aday | Pozisyon | `baslangic?`, `bitis?` |
| `MEZUN` | Aday | Egitim | `derece?`, `mezuniyet_yili?` |
| `TAMAMLADI` | Aday | Sertifika | `yil?` |
| `PROJEDE_YER_ALDI` | Aday | Proje | `rol?` |
| `KULLANDI` | Proje | Yetenek | — |

### ID Formatı

```
{node_tipi_prefix}_{isim_lowercase_underscore}

Örnekler:
  aday_jaroslav_chechnik
  skill_python
  sirket_tata_motors
  egitim_vit_ap_university
  proje_smart_parking_system
```

**Kurallar:**
- Sadece lowercase harf, rakam, underscore
- Türkçe karakter yok (ş→s, ı→i, ö→o, ü→u, ç→c, ğ→g)
- Prefix zorunlu: `aday_`, `skill_`, `sirket_`, `pozisyon_`, `egitim_`, `sertifika_`, `proje_`

---

## Kod Standartları

### Genel Kurallar

- **Pydantic v2** kullan: `model_dump()`, `model_validate_json()`, `model_json_schema()`
- `model.schema()` veya `model.dict()` kullanma — Pydantic v1 API'si
- Her yeni implementasyon `src/base.py`'daki abstract sınıftan türemeli
- `CVPipeline`'a dokunma — extractor/embedder/writer dışarıdan inject edilir

### Hata Yönetimi

- Her LLM çağrısında max 2 retry
- 429 hatası alınca **60 saniye** bekle, sonra retry yap
- `run_all()` içinde her istek arasında **5 saniye** `time.sleep`
- Hata olan CV'yi atla, geri kalanları işlemeye devam et

### Environment Variables

```bash
GROQ_API_KEY=...     # Extraction için (llama-3.3-70b-versatile)
OPENAI_API_KEY=...   # Embedding için (text-embedding-3-large)
```

`.env` dosyası git'e gitmez. Yeni değişken eklenince hem `.env`'e hem bu dokümana yaz.

### Import Sırası

```python
# 1. Standart kütüphane
import os, time, json

# 2. Üçüncü parti
from openai import OpenAI

# 3. Proje içi
from src.schema import GraphData
from src.base import BaseExtractor
```

---

## Aşama Durumu

| Aşama | Ne | Durum |
|-------|----|-------|
| 1 | Kural tabanlı extraction | ✅ Tamamlandı (arşivde) |
| 2 | LLM extraction (Groq llama-3.3-70b-versatile) | ✅ Tamamlandı |
| 3 | Embedding (OpenAI text-embedding-3-large) | ✅ Tamamlandı |
| 4 | Memgraph'a yazma + Node2Vec | ⏳ Bekliyor |
| 5 | RAG Pipeline | ⏳ Bekliyor |
| 6 | LangGraph Agent | ⏳ Bekliyor |

---

## Aşama 3 — Embedding Detayı

**Model:** `text-embedding-3-large` (OpenAI)
**Boyut:** 3072-dim
**Kütüphane:** `openai`

**Ne embed edilir:**
- `Yetenek` node'ları: `name` field'ı
- `Pozisyon` node'ları: `name` field'ı
- `Proje` node'ları: `name + aciklama` birleşimi
- `Sirket` node'ları: `name` field'ı
- `Aday` node'ları embed edilmez

**Çıktı:** Her entity'nin `properties` dict'ine `embedding: List[float]` eklenir

**Rate limit:** Dakikada 1500 token — `time.sleep(0.1)` yeterli

---

## Aşama 4 — Memgraph Detayı

**Bağlantı:** Bolt protokolü, `neo4j` Python driver  
**Port:** 7687 (default)  
**Query dili:** Cypher

Node yaratma şablonu:
```cypher
MERGE (n:Yetenek {id: $id})
SET n.name = $name, n.embedding = $embedding
```

---

## Multi-Language Hazırlığı

Node label'ları ve relation tipleri `src/labels.py`'da merkezi olarak tanımlı.  
Dil değişikliği gerekirse sadece bu dosya güncellenir.  
Kod içinde string literal (`"Yetenek"`, `"SAHIP"`) kullanma — her zaman `labels.py`'dan import et.

---

## Git Kuralları

```
.gitignore içermeli:
  .env
  output/
  __pycache__/
  *.pyc
  .venv/
```

Commit mesajı formatı:
```
[Aşama N] Ne yapıldı

Örnek:
  [Aşama 2] Gemini extractor rate limit koruması eklendi
  [Aşama 3] OpenAIEmbedder implementasyonu tamamlandı
```