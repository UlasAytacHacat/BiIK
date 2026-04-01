# BiIK — Proje Standartları ve Geliştirme Rehberi

## Proje Özeti

BiIK, Türkçe HR ekipleri için CV'lerden knowledge graph üreten ve GraphRAG tabanlı aday öneri sistemi kuran bir Python pipeline'ıdır.

**Teknoloji yığını:** Python 3.10+ · Pydantic v2 · Groq API · OpenAI API · Memgraph · LangGraph
**Geliştirme ortamı:** Windows, VS Code + Claude Code

---

## Klasör Yapısı

```
BiIK/
├── data/                     # Ham CV JSON'ları
├── output/                   # İşlenmiş graph JSON'lar + .written sentinel'ları
├── uploads/                  # Yüklenen ham dosyalar
├── src/
│   ├── base.py               # Abstract sınıflar (BaseExtractor, BaseEmbedder, BaseWriter)
│   ├── schema.py             # Pydantic modelleri (Entity, Relationship, GraphData)
│   ├── labels.py             # Node label ve relation tip sabitleri — TEK KAYNAK
│   ├── prompts.py            # Türkçe sistem promptu
│   ├── groq_extractor.py     # LLM extraction — Groq llama-3.3-70b-versatile
│   ├── openai_embedder.py    # Embedding — OpenAI text-embedding-3-large
│   ├── memgraph_writer.py    # Graph DB yazıcı — batch Cypher + index yönetimi
│   ├── node2vec_config.py    # Node2Vec parametreleri — Node2VecConfig dataclass
│   └── node2vec_runner.py    # Node2Vec çalıştırıcı — Node2VecRunner sınıfı
├── api/
│   ├── main.py               # FastAPI app, CORS, router kayıtları
│   └── routes/
│       ├── ingest.py         # POST /ingest
│       ├── convert.py        # POST /convert
│       ├── extract.py        # POST /extract (singleton GroqExtractor)
│       ├── embed.py          # POST /embed (singleton OpenAIEmbedder)
│       ├── write.py          # POST /write (singleton MemgraphWriter + sentinel)
│       ├── candidates.py     # GET /candidates
│       └── reindex.py        # POST /reindex — Node2Vec tetikleyici
├── requirements.txt
├── .env                      # API key'ler (git'e gitmesin)
├── .gitignore
└── CLAUDE.md                 # Bu dosya
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
- **String literal label/type kullanma** — her zaman `src/labels.py`'dan import et:
  ```python
  from src.labels import NODE_YETENEK, REL_CALISTI  # doğru
  entity.label == "Yetenek"                          # yanlış
  ```

### Singleton Pattern (API route'ları)

Her route modülünde extractor/embedder/writer modül seviyesinde tek instance olarak tutulur:
```python
_extractor: GroqExtractor | None = None

def get_extractor() -> GroqExtractor:
    global _extractor
    if _extractor is None:
        _extractor = GroqExtractor()
    return _extractor
```
Bu pattern `extract.py`, `embed.py`, `write.py` içinde uygulanmıştır.

### Hata Yönetimi

- Her LLM çağrısında max 4 retry
- 429 hatası alınca hata mesajındaki `"try again in Xs"` değeri parse edilir, üstüne 5s eklenerek beklenir
- Default fallback: 60 saniye
- Hata olan adımı atla, diğerlerine devam et

### Environment Variables

```bash
GROQ_API_KEY=...        # Extraction için (llama-3.3-70b-versatile)
OPENAI_API_KEY=...      # Embedding için (text-embedding-3-large)
MEMGRAPH_URI=...        # Opsiyonel, default: bolt://localhost:7687
MEMGRAPH_USER=...       # Opsiyonel
MEMGRAPH_PASSWORD=...   # Opsiyonel
```

`.env` dosyası git'e gitmez. Yeni değişken eklenince hem `.env`'e hem bu dokümana yaz.

### Import Sırası

```python
# 1. Standart kütüphane
import os, time, json

# 2. Üçüncü parti
from openai import OpenAI

# 3. Proje içi
from src.labels import NODE_YETENEK, REL_CALISTI
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
| 4 | Memgraph'a yazma + Node2Vec | ✅ Tamamlandı |
| 5 | RAG Pipeline | ⏳ Bekliyor |
| 6 | LangGraph Agent | ⏳ Bekliyor |

---

## Aşama 3 — Embedding Detayı

**Model:** `text-embedding-3-large` (OpenAI)
**Boyut:** 3072-dim
**Kütüphane:** `openai`

**Ne embed edilir** (`src/labels.py` → `EMBEDDABLE_LABELS`):
- `Yetenek`: `name` field'ı
- `Pozisyon`: `name` field'ı
- `Proje`: `name + aciklama` birleşimi
- `Sirket`: `name` field'ı
- `Egitim`: `name` field'ı
- `Aday` embed edilmez

**Çıktı:** Her entity'nin `properties` dict'ine `embedding: List[float]` eklenir
**Rate limit:** Dakikada 1500 token — `time.sleep(0.1)` yeterli

---

## Aşama 4 — Memgraph + Node2Vec Detayı

**Bağlantı:** Bolt protokolü, `neo4j` Python driver, port 7687
**Query dili:** Cypher
**Singleton:** `api/routes/write.py` → `get_writer()` — driver bağlantısı yeniden kullanılır

### Index Yönetimi

`MemgraphWriter.__init__` içinde otomatik çalışır:
- **ID index:** Tüm node label'ları için `CREATE INDEX ON :Label(id)` — sorgu hızı
- **Vector index:** `EMBEDDABLE_LABELS` için `vector_search.create_index(...)` — Aşama 5 araması

### Sentinel Mekanizması

`POST /write` başarıyla tamamlanınca `output/{stem}_graph.written` dosyası oluşturulur.
Aynı dosya tekrar gönderilirse Memgraph'a yazmadan `{cached: true}` döner.
`GET /candidates` bu dosyayı kontrol ederek `"written"` status'unu belirler.

### Node2Vec

**Config:** `src/node2vec_config.py` → `Node2VecConfig` dataclass
**Runner:** `src/node2vec_runner.py` → `Node2VecRunner` sınıfı
**Endpoint:** `POST /reindex` — query param'larla config override edilebilir

```
POST /reindex                           → default config (p=2.0, q=0.5, size=64)
POST /reindex?p=1.0&q=1.0              → random walk (BFS/DFS dengesi)
POST /reindex?vector_size=128           → daha büyük vektör
```

Tune etmek için `src/node2vec_config.py` içindeki `DEFAULT_CONFIG`'i değiştir
veya `/reindex` endpoint'ini farklı query param'larla çağır.

> **Aşama 5 başlamadan önce `POST /reindex` çalıştırılmalıdır.**

---

## Batch Transaction

`MemgraphWriter` node ve relation'ları label/type bazında gruplandırarak `UNWIND` ile yazar:
```cypher
UNWIND $nodes AS node
MERGE (n:Yetenek {id: node.id})
SET n += node.props
```
Her CV için iki transaction: biri tüm node'lar, biri tüm relation'lar.

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

Örnekler:
  [Aşama 4] Node2Vec runner ve reindex endpoint eklendi
  [Aşama 4] labels.py ile string literal tutarsızlıkları giderildi
```
