from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from src.labels import NODE_ADAY, NODE_EGITIM, NODE_YETENEK, REL_CALISTI
from src.schema import GraphData

OUTPUT_DIR = Path("output")

router = APIRouter()


@router.get("/candidates")
def list_candidates():
    results = []

    for path in sorted(OUTPUT_DIR.glob("*_graph.json")):
        try:
            graph_data = GraphData.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        aday = next((e for e in graph_data.entities if e.label == NODE_ADAY), None)
        if not aday:
            continue

        name = aday.properties.get("name", path.stem)

        skills = [
            e.properties.get("name", "")
            for e in graph_data.entities
            if e.label == NODE_YETENEK
        ]

        entity_by_id = {e.id: e for e in graph_data.entities}

        companies = []
        for rel in graph_data.relationships:
            if rel.type == REL_CALISTI:
                sirket = entity_by_id.get(rel.target)
                if sirket:
                    companies.append({
                        "name": sirket.properties.get("name", ""),
                        "role": rel.properties.get("rol", ""),
                    })

        education = []
        for e in graph_data.entities:
            if e.label == NODE_EGITIM:
                education.append({
                    "degree": e.properties.get("derece", ""),
                    "institution": e.properties.get("kurum", ""),
                })

        if (OUTPUT_DIR / (path.stem + ".written")).exists():
            status = "written"
        elif any(len(e.properties.get("embedding", [])) > 0 for e in graph_data.entities):
            status = "embedded"
        else:
            status = "extracted"

        results.append({
            "id": path.stem,
            "name": name,
            "skillCount": len(skills),
            "companyCount": len(companies),
            "status": status,
            "skills": skills,
            "companies": companies,
            "education": education,
        })

    return results
