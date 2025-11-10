# app/models.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class Source(SQLModel, table=True):
    domain: str = Field(primary_key=True)
    name: Optional[str] = None
    bayes_prior_truth: float = 0.5
    bias: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: Optional[str] = None
    domain: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_text: Optional[str] = None
    clean_text: Optional[str] = None
    language: Optional[str] = "en"

class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id")
    text: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    topic: Optional[str] = None

class Evidence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claim.id")
    type: str  # "fact_check"
    source_name: str
    source_url: str
    stance: str  # supports|refutes|mixed|unrelated
    similarity: float
    snippet: Optional[str] = None

class Verification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id")
    source_prior: float
    text_consistency: float
    cross_reference: float
    combined_confidence: float
    explanation: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
