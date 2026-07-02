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
    searches_completed: int = 0
    pages_downloaded: int = 0
    pages_summarized: int = 0
    failed_pages: List[str] = Field(default_factory=list)
    sources_collected: List[str] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    report_status: str = "not_started"

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
