# app/schema.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    url: Optional[HttpUrl] = None
    text: Optional[str] = None

class EvidenceOut(BaseModel):
    type: str
    source_name: str
    source_url: str
    stance: str
    similarity: float
    snippet: Optional[str] = None

class ClaimOut(BaseModel):
    text: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    evidences: List[EvidenceOut] = []

class AnalyzeResponse(BaseModel):
    domain: Optional[str]
    source_prior: float
    text_consistency: float
    cross_reference: float
    combined_confidence: float
    verdict_label: str
    explanation: str
    claims: List[ClaimOut]
