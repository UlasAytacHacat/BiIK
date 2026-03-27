import json
from src.schema import GraphData, Entity, Relationship

class GraphExtractor:
    def __init__(self):
        print("[SİSTEM] Kural Tabanlı Analiz Modu Aktif (Offline)...")

    def extract_graph_data(self, text: str, annotations: list = None) -> GraphData:
        """
        Ham metinden ve etiketlerden (annotations) Varlık ve İlişkileri çıkarır.
        LLM bağlantısı gerekmez.
        """
        entities = []
        relationships = []
        
        # 1. ADAY İSMİNİ ÇIKAR (Metnin ilk satırını veya annotations'ı kullan)
        # Genellikle CV'nin ilk satırı isimdir. Eğer boşsa 'Bilinmeyen Aday' yapalım.
        candidate_name = text.strip().split('\n')[0].strip() or "Bilinmeyen Aday"
        candidate_id = candidate_name.lower().replace(" ", "_")
        
        # Aday Varlığını Ekle
        entities.append(Entity(id=candidate_id, label="Aday", properties={"name": candidate_name}))
        
        # 2. YETENEKLERİ (SKILLS) ÇIKAR (Annotations kısmından)
        if annotations:
            # Tekrar eden yetenekleri engellemek için set kullanalım
            seen_skills = set()
            
            for start, end, label in annotations:
                if label.startswith("SKILL:"):
                    # Etiketten 'SKILL:' kısmını atıp gerçek yeteneği alalım
                    skill_name = label.replace("SKILL:", "").strip()
                    skill_id = f"skill_{skill_name.lower().replace(' ', '_')}"
                    
                    if skill_id not in seen_skills:
                        # Yetenek Varlığını Ekle
                        entities.append(Entity(id=skill_id, label="Yetenek", properties={"name": skill_name}))
                        
                        # Aday ve Yetenek arasındaki İlişkiyi Ekle
                        relationships.append(Relationship(
                            source=candidate_id,
                            target=skill_id,
                            type="SAHIP"
                        ))
                        seen_skills.add(skill_id)
        
        # 3. ŞİRKET/EĞİTİM (Opsiyonel - Metin analizinden basit kurallar)
        # Örnek metinde 'One97 Communications Limited' geçiyor, bunu Şirket olarak ekleyebiliriz.
        first_line = text.strip().split('\n')[0]
        if "Communications" in first_line or "Limited" in first_line:
             company_id = first_line.lower().replace(" ", "_")
             entities.append(Entity(id=company_id, label="Sirket", properties={"name": first_line}))
             relationships.append(Relationship(source=candidate_id, target=company_id, type="CALISTI"))

        return GraphData(entities=entities, relationships=relationships)