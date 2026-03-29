from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class Node2VecConfig:
    directed: bool = False
    p: float = 2.0          # Geri dönme olasılığı — yüksek = daha fazla keşif
    q: float = 0.5          # Uzağa gitme olasılığı — düşük = yapısal odak
    num_walks: int = 4      # Her node'dan kaç yol denensin
    walk_length: int = 5    # Her yol kaç adım atsın
    vector_size: int = 64   # Üretilen vektör boyutu (test: 2, prod: 64-128)
    embedding_property: str = "n2v_embedding"  # Node'a yazılacak property adı
    metric: Literal["cos", "l2"] = "cos"       # Vektör benzerlik metriği


# Tune etmek için sadece burayı değiştir — veya POST /reindex?p=...&q=... kullan
DEFAULT_CONFIG = Node2VecConfig()
