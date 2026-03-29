from typing import List
from pydantic import BaseModel, Field


class Entity(BaseModel):
    id: str
    label: str
    properties: dict = Field(default_factory=dict)


class Relationship(BaseModel):
    source: str
    target: str
    type: str
    properties: dict = Field(default_factory=dict)


class GraphData(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
