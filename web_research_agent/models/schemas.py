from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict

class ResearchPlan(BaseModel):
    topic: str
    queries: List[str]
    objectives: List[str]

class ArticleSummary(BaseModel):
    url: str
    summary: str

class ResearchState(BaseModel):
    query: str
    plan: Optional[ResearchPlan] = None
    urls_found: int = 0
    urls_processed: int = 0
    successful_downloads: int = 0
    successful_extractions: int = 0
    successful_summaries: int = 0
    failed_pages: List[Dict[str, str]] = Field(default_factory=list) # List of {url, reason}
    sources_collected: List[str] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    report_status: str = "not_started"
    confidence_score: float = 0.0

class ResearchReport(BaseModel):
    title: str
    executive_summary: str
    research_objectives: List[str]
    methodology: str
    source_summaries: List[ArticleSummary]
    final_conclusion: str
    coverage_summary: str
    confidence_score: float
    known_gaps: List[str]
    references: List[str]
