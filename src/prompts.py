EXTRACTION_PROMPT = """\
CV metninden knowledge graph çıkar. Sadece CV'de açıkça geçen bilgileri ekle.

## NODE TİPLERİ
label field'ı kesinlikle şu 7 değerden biri olmalı: Aday, Yetenek, Sirket, Pozisyon, Egitim, Sertifika, Proje
İş unvanları (Engineer, Analyst, Manager, Developer vb.) Yetenek olarak çıkarılmaz. Sadece teknik beceriler, araçlar ve teknolojiler Yetenek node'u olur.
Varlığın adı veya başka herhangi bir şey yazılmamalı — yalnızca bu 7 değerden biri.
ID format: {tip_prefix}_{isim} — küçük harf, boşluk yerine alt çizgi
Prefixler: aday_, skill_, sirket_, pozisyon_, egitim_, sertifika_, proje_

## İLİŞKİ YÖNLERİ (source → target)
SAHIP: Aday → Yetenek
POZISYONUNDA: Aday → Pozisyon
CALISTI: Aday → Sirket (properties: rol, baslangic, bitis)
MEZUN: Aday → Egitim (properties: derece, mezuniyet_yili)
TAMAMLADI: Aday → Sertifika (properties: yil)
PROJEDE_YER_ALDI: Aday → Proje
KULLANDI: Proje → Yetenek

## KURALLAR
- Aday node'u her zaman properties: {"name": "adayın tam adı"} içermeli.
- Yetenek node'u her zaman properties: {"name": "skill adı"} içermeli. Boş properties kabul edilmez.
- Yetenek ID prefix'i kesinlikle skill_ olmalı. yetenek_ prefix'i kullanılmaz.
- Yetenek: yalnızca teknik/mesleki beceriler. Bölüm başlıkları, kişisel bilgiler, jenerik kelimeler yetenek değildir.
- Proje.aciklama: yalnızca projenin ne yaptığı. Tarih, rol, şirket adı ekleme.
- Aynı varlık birden fazla ilişkide geçiyorsa aynı ID kullan.

## ÇIKTI FORMATI
{"entities":[{"id":"...","label":"...","properties":{}}],"relationships":[{"source":"...","target":"...","type":"...","properties":{}}]}
"""
