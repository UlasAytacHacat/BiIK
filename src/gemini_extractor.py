from __future__ import annotations

import os
import time

from google import genai
from google.genai import types

from src.base import BaseExtractor
from src.schema import GraphData

SYSTEM_PROMPT = """\
CV metninden knowledge graph çıkar. Sadece CV'de açıkça geçen bilgileri ekle.

## NODE TİPLERİ
Aday, Yetenek, Sirket, Pozisyon, Egitim, Sertifika, Proje
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
- Yetenek: yalnızca teknik/mesleki beceriler. Bölüm başlıkları, kişisel bilgiler, jenerik kelimeler yetenek değildir.
- Proje.aciklama: yalnızca projenin ne yaptığı. Tarih, rol, şirket adı ekleme.
- Aynı varlık birden fazla ilişkide geçiyorsa aynı ID kullan.

## ÇIKTI FORMATI
{"entities":[{"id":"...","label":"...","properties":{}}],"relationships":[{"source":"...","target":"...","type":"...","properties":{}}]}
"""

_INTER_REQUEST_DELAY = 5
_RETRY_WAIT_429 = 60
_MAX_RETRIES = 2


class GeminiExtractor(BaseExtractor):
    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        self.model = model
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self._request_count = 0
        print(f"[SİSTEM] Gemini Extraction Modu Aktif ({self.model})...")

    def extract(self, text: str, annotations: list = None) -> GraphData:
        if self._request_count > 0:
            time.sleep(_INTER_REQUEST_DELAY)
        self._request_count += 1

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0,
            max_output_tokens=8192,
        )

        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=f"CV metni:\n\n{text}",
                    config=config,
                )
                return GraphData.model_validate_json(response.text)

            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_WAIT_429 if "429" in str(exc) else 0
                    msg = f"  [RETRY {attempt}/{_MAX_RETRIES}] {exc}"
                    if wait:
                        msg += f" — {wait}s bekleniyor"
                    print(msg)
                    if wait:
                        time.sleep(wait)

        raise RuntimeError(
            f"GeminiExtractor {_MAX_RETRIES} denemede başarısız: {last_error}"
        )
