from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any

class ResearchPlan(BaseModel):
    topic: str
    queries: List[str]
    objectives: List[str]

class ArticleSummary(BaseModel):
    url: str
    summary: str

class Contradiction(BaseModel):
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    explanation: Optional[str] = None

class ReasoningResult(BaseModel):
    completed_objectives: List[str]
    missing_objectives: List[str]
    contradictions: List[Contradiction] = Field(default_factory=list)
    confidence: float # 0-100
    objective_coverage: Dict[str, float] # objective: coverage %
    follow_up_queries: List[str] = Field(default_factory=list)
    continue_research: bool

class KnowledgeBaseEntry(BaseModel):
    summary: str
    source: str
    confidence: float
    covered_objectives: List[str]
    supporting_evidence: str

class ResearchState(BaseModel):
    query: str
    plan: Optional[ResearchPlan] = None
    iterations: int = 0
    urls_found: int = 0
    urls_processed: int = 0
    successful_downloads: int = 0
    successful_extractions: int = 0
    successful_summaries: int = 0
    failed_pages: List[Dict[str, str]] = Field(default_factory=list)
    sources_collected: List[str] = Field(default_factory=list)
    knowledge_base: List[KnowledgeBaseEntry] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    objective_coverage: Dict[str, float] = Field(default_factory=dict)
    follow_up_queries: List[str] = Field(default_factory=list)
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
    iterations_performed: int
    coverage_matrix: Dict[str, float]
    contradictions: List[Contradiction]
    evidence_summary: str
