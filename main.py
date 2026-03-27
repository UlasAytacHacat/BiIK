import os
import json
import shutil  # Klasör silme işlemi için eklendi
from dotenv import load_dotenv
from src.extractor import GraphExtractor

load_dotenv()

def process_all_cvs(data_folder="data", output_folder="output"):
    # --- YENİ: KLASÖR TEMİZLEME İŞLEMİ ---
    if os.path.exists(output_folder):
        print(f"(!) '{output_folder}' klasörü temizleniyor...")
        shutil.rmtree(output_folder) # Klasörü ve içindeki her şeyi siler
    
    os.makedirs(output_folder) # Klasörü yeniden tertemiz oluşturur
    # -------------------------------------

    extractor = GraphExtractor()
    
    json_files = [f for f in os.listdir(data_folder) if f.endswith('.json')]
    
    if not json_files:
        print(f"(!) '{data_folder}' klasöründe hiç JSON bulunamadı.")
        return

    print(f"--- Toplam {len(json_files)} dosya işleniyor (Kural Tabanlı & Temiz Başlangıç) ---")

    for filename in json_files:
        try:
            print(f"\n[İŞLENİYOR] {filename}...")
            json_path = os.path.join(data_folder, filename)
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_text = data.get("text", "")
                annotations = data.get("annotations", [])
            
            if not raw_text.strip():
                print(f"    [UYARI] {filename} metni boş, atlanıyor.")
                continue

            # Extractor veriyi hazırlar
            graph_results = extractor.extract_graph_data(raw_text, annotations)
            
            output_filename = f"{os.path.splitext(filename)[0]}_graph.json"
            output_path = os.path.join(output_folder, output_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(graph_results.model_dump(), f, indent=4, ensure_ascii=False)
            
            print(f"    [TAMAM] {output_filename} oluşturuldu.")
            
        except Exception as e:
            print(f"    [HATA] {filename} işlenirken hata oluştu: {e}")

    print("\n--- Tüm süreç başarıyla tamamlandı! ---")

if __name__ == "__main__":
    process_all_cvs()