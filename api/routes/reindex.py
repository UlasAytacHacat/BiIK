from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.node2vec_config import DEFAULT_CONFIG, Node2VecConfig
from src.node2vec_runner import Node2VecRunner

router = APIRouter()


@router.post("/reindex")
async def reindex(
    p: float = Query(DEFAULT_CONFIG.p, description="Geri dönme olasılığı"),
    q: float = Query(DEFAULT_CONFIG.q, description="Uzağa gitme olasılığı"),
    num_walks: int = Query(DEFAULT_CONFIG.num_walks, description="Her node'dan kaç yol"),
    walk_length: int = Query(DEFAULT_CONFIG.walk_length, description="Her yol kaç adım"),
    vector_size: int = Query(DEFAULT_CONFIG.vector_size, description="Vektör boyutu"),
):
    """
    Node2Vec'i tüm graph üzerinde çalıştırır.
    Query param'larla config override edilebilir.

    Örnekler:
      POST /reindex                          → default config
      POST /reindex?p=1.0&q=1.0             → random walk (BFS/DFS dengesi)
      POST /reindex?vector_size=128          → daha büyük vektör
    """
    config = Node2VecConfig(
        p=p,
        q=q,
        num_walks=num_walks,
        walk_length=walk_length,
        vector_size=vector_size,
    )

    try:
        from api.routes.write import get_writer
        writer = get_writer()
        runner = Node2VecRunner(
            session_factory=writer._driver.session,
            config=config,
        )
        result = runner.run()
        verification = runner.verify()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "result": result, "verification": verification}
