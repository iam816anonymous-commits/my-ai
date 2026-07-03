from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class QueryIntent(str, Enum):
    BIOGRAPHY = "Biography"
    TECHNOLOGY = "Technology"
    PROGRAMMING = "Programming"
    FINANCE = "Finance"
    MEDICAL = "Medical"
    CYBERSECURITY = "Cybersecurity"
    HISTORY = "History"
    BUSINESS = "Business"
    GENERAL = "General"

class KnowledgeBaseEntry(BaseModel):
    summary: str
    source: str
    confidence: float
    covered_objectives: List[str]
    supporting_evidence: str

class ResearchPlan(BaseModel):
    topic: str
    intent: QueryIntent
    queries: List[str]
    objectives: List[str]

class ArticleSummary(BaseModel):
    url: str
    summary: str
    quality_score: float = 0.0
    source_type: str = "Unknown"
    source_tier: int = 5
    title: Optional[str] = None
    publication_date: Optional[str] = None

class Contradiction(BaseModel):
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    explanation: Optional[str] = None

class EvidenceItem(BaseModel):
    claim: str
    supporting_sources: List[str]
    source_types: List[str] = Field(default_factory=list)
    confidence: float # 0-100
    evidence_strength: str # Strong, Medium, Weak
    strength_justification: str = ""
    agreement_score: float # 0-100
    publication_dates: List[str] = Field(default_factory=list)

class EvidenceGraph(BaseModel):
    items: List[EvidenceItem] = Field(default_factory=list)

class ConfidenceBreakdown(BaseModel):
    overall: float
    coverage: float
    evidence_strength: float
    source_diversity: float
    agreement: float
    extraction_quality: float
    missing_evidence_penalty: float
    contradiction_penalty: float

class ResearchGap(BaseModel):
    topic: str
    reason_missing: str = ""
    suggested_queries: List[str]
    recommended_authoritative_sources: List[str] = Field(default_factory=list)
    estimated_confidence_improvement: float = 0.0

class ReasoningResult(BaseModel):
    completed_objectives: List[str]
    missing_objectives: List[str]
    contradictions: List[Contradiction] = Field(default_factory=list)
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    objective_coverage: Dict[str, float]
    follow_up_queries: List[str] = Field(default_factory=list)
    continue_research: bool
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    gaps: List[ResearchGap] = Field(default_factory=list)

class ProfilingStats(BaseModel):
    stages: Dict[str, float] = Field(default_factory=dict)
    prompt_tokens: int = 0
    response_tokens: int = 0
    llm_calls: int = 0
    cache_hits: int = 0

class SourceV2Info(BaseModel):
    url: str
    score: float
    tier: int = 5
    type: str
    rejection_reason: Optional[str] = None

class SearchHealth(BaseModel):
    success_rate: float = 1.0
    timeouts: int = 0
    errors_403: int = 0
    errors_429: int = 0
    captcha_count: int = 0
    avg_latency: float = 0.0

class ResearchState(BaseModel):
    query: str
    plan: Optional[ResearchPlan] = None
    iterations: int = 0
    urls_found: int = 0
    urls_rejected: List[SourceV2Info] = Field(default_factory=list)
    successful_downloads: int = 0
    failed_downloads: int = 0
    successful_extractions: int = 0
    successful_summaries: int = 0
    fallback_summaries_used: int = 0
    sources_collected: List[str] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    evidence_graph: EvidenceGraph = Field(default_factory=EvidenceGraph)
    objective_coverage: Dict[str, float] = Field(default_factory=dict)
    confidence_evolution: List[float] = Field(default_factory=list)
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    gaps: List[ResearchGap] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    profiling: ProfilingStats = Field(default_factory=ProfilingStats)
    knowledge_base: List[KnowledgeBaseEntry] = Field(default_factory=list)
    confidence_score: float = 0.0
    search_health: Dict[str, SearchHealth] = Field(default_factory=dict)
    follow_up_queries: List[str] = Field(default_factory=list)

class SelfEvaluation(BaseModel):
    overall_grade: str
    justification: str
    coverage_score: float = 0.0
    evidence_score: float = 0.0
    readability_score: float = 0.0
    citation_quality: float = 0.0
    objectivity: float = 0.0
    bias_risk: float = 0.0
    novel_insights: float = 0.0

class ResearchReport(BaseModel):
    title: str
    executive_dashboard: Dict[str, Any]
    scorecard: Dict[str, float]
    key_takeaways: List[str]
    detailed_analysis: str
    supporting_evidence: List[EvidenceItem]
    contradictions: List[Contradiction]
    research_gaps: List[ResearchGap]
    confidence_breakdown: ConfidenceBreakdown
    references: List[str]
    further_reading: List[str]

class BenchmarkMetrics(BaseModel):
    query: str
    category: str
    runtime: float
    pages_searched: int
    successful_downloads: int
    extraction_success: int
    summary_success: int
    evidence_count: int
    citation_count: int
    coverage: float
    confidence: float
    overall_quality_score: float
    grade: str
    memory_peak_mb: float
    source_quality_avg: float
    timestamp: datetime = Field(default_factory=datetime.now)
