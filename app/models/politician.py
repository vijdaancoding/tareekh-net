from pydantic import BaseModel
from typing import Optional


class PoliticianResponse(BaseModel):
    id: str
    name: str
    born: Optional[str] = None
    bio: Optional[str] = None


class PoliticianDetailResponse(BaseModel):
    politician: dict
    relationships: list[dict]


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    results: list[dict] = []
