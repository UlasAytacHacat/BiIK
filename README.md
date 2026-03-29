# BiIK - CV'den Bilgi Grafına (CV-to-Graph) Dönüşüm Hattı

Bu proje, yapılandırılmamış veya yarı-yapılandırılmış CV verilerini (Annotated JSON/PDF) alarak, varlıklar ve ilişkilerden oluşan bir **Anlamsal Ağ (Graph)** yapısına dönüştüren bir pipeline çalışmasıdır.

## Proje Mimari Akışı
1. **Parsing:** Ham metin ve etiketlerin (annotations) ayrıştırılması.
2. **Entity Extraction:** Aday, Yetenek ve Şirket düğümlerinin (Nodes) oluşturulması.
3. **Relationship Extraction:** Düğümler arası semantik bağların (SAHIP, CALISTI) kurulması.
4. **Output:** Memgraph/Neo4j gibi Graph veritabanlarına uyumlu JSON çıktısı üretimi.

## Teknolojiler
- **Python 3.10+**
- **Pydantic:** Veri şeması ve doğrulama.
- **LangChain & OpenAI:** (Gelecek aşamalar için LLM entegrasyonu hazır).

## Klasör Yapısı
- `src/`: Core mantık ve şemalar.
- `data/`: İşlenecek CV verileri.
- `output/`: Üretilen Graph-JSON dosyaları.

## Memgraph
- docker run -it -p 7687:7687 -p 7444:7444 -p 3000:3000 --name memgraph memgraph/memgraph-platform
- localhost:3000 memgraph arayüz
- localhost:7687 memgraph 

## Run
- uvicorn api.main:app --reload --port 8000
- npm run dev
