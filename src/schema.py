from typing import List, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    id: str = Field(description="Varlık için benzersiz bir ID (örn: aday_ismi, sirket_ismi)")
    label: str = Field(description="Varlık tipi: Aday, Yetenek, Sirket, Pozisyon, Egitim, Sertifika, Proje")
    properties: dict = Field(default_factory=dict, description="Varlık özellikleri (isim, seviye, yil vb.)")

class Relationship(BaseModel):
    source: str = Field(description="İlişkinin başladığı varlık ID'si")
    target: str = Field(description="İlişkinin bittiği varlık ID'si")
    type: str = Field(description="İlişki tipi (CALISTI, SAHIP, MEZUN, PROJEDE_YER_ALDI)")
    properties: dict = Field(default_factory=dict, description="İlişki özellikleri (sure, seviye, rol vb.)")

class GraphData(BaseModel):
    entities: List[Entity] = Field(description="Metinden çıkarılan tüm düğümler")
    relationships: List[Relationship] = Field(description="Düğümler arasındaki tüm bağlantılar")