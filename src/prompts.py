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

## NODE PROPERTIES ZORUNLULUKLARI
Her node tipi için properties kesinlikle dolu olmalı. Boş {} kesinlikle kabul edilmez.

- Aday      → properties: {"name": "adayın tam adı"}
- Yetenek   → properties: {"name": "skill adı"}
- Sirket    → properties: {"name": "şirket adı"}
- Pozisyon  → properties: {"name": "pozisyon/unvan adı"}
- Egitim    → properties: {"derece": "lisans/yüksek lisans/önlisans vb.", "kurum": "okul adı", "yil": "mezuniyet yılı (varsa)"}
- Sertifika → properties: {"name": "sertifika adı", "yil": "alınış yılı (varsa)"}
- Proje     → properties: {"name": "proje adı", "aciklama": "projenin ne yaptığı (varsa)"}

ID'den isim türetilebilir: "sirket_google" → name: "Google", "pozisyon_software_engineer" → name: "Software Engineer", "sertifika_aws_cloud_practitioner" → name: "AWS Cloud Practitioner".

## KURALLAR
- Yetenek ID prefix'i kesinlikle skill_ olmalı. yetenek_ prefix'i kullanılmaz.
- Yetenek: yalnızca teknik/mesleki beceriler. Bölüm başlıkları, kişisel bilgiler, jenerik kelimeler yetenek değildir.
- Proje.aciklama: yalnızca projenin ne yaptığı. Tarih, rol, şirket adı ekleme.
- Aynı varlık birden fazla ilişkide geçiyorsa aynı ID kullan.

## ÇIKTI FORMATI
{"entities":[{"id":"...","label":"...","properties":{}}],"relationships":[{"source":"...","target":"...","type":"...","properties":{}}]}
"""
