import json

class CVParser:
    def extract_text_from_json(self, json_path: str) -> str:
        """Annotated JSON dosyasını okur ve içindeki ham metni döner."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("text", "")