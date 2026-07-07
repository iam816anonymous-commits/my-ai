from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, TypeVar, Generic
from datetime import datetime
from enum import Enum

T = TypeVar("T")

class ResearchRequest(BaseModel):
    """Module 19: REST API Request schema."""
    query: str

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

class ObjectiveStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    SEARCHING = "SEARCHING"
    FETCHING = "FETCHING"
    SUMMARIZING = "SUMMARIZING"
    EVIDENCE_FOUND = "EVIDENCE_FOUND"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class PipelineResult(BaseModel, Generic[T]):
    success: bool
    payload: Optional[T] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timing: float = 0.0
    stage: str = ""

class FetchResult(BaseModel):
    """Module 5: Browser engine output."""
    html_map: Dict[str, str]
    total_latency: float

class ExtractionResult(BaseModel):
    """Module 6: Extraction engine output."""
    texts_map: Dict[str, str]
    valid_count: int
    rejected_count: int

class SearchResult(BaseModel):
    """Module 2: Search engine output."""
    scored_urls: List["SourceV2Info"]
    rejected_urls: List["SourceV2Info"]
    health: Dict[str, "SearchHealth"]

class ObjectiveState(BaseModel):
    objective: str
    status: ObjectiveStatus = ObjectiveStatus.NOT_STARTED
    coverage: float = 0.0 # 0-100
    evidence_count: int = 0
    confidence: float = 0.0
    missing_evidence: str = ""
    search_attempts: int = 0
    number_of_sources: int = 0
    source_diversity: float = 0.0
    contradictions_count: int = 0
    last_update_iteration: int = 0

class SourceDocument(BaseModel):
    """Module 8 & 9: Rich structured document schema."""
    id: str
    url: str
    title: Optional[str] = None
    authority_score: float = 0.0
    published_date: Optional[str] = None
    domain: str = ""
    clean_text: str
    summary: str
    entities: List[str] = Field(default_factory=list)
    claims: List[str] = Field(default_factory=list)
    quotes: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    embeddings: List[float] = Field(default_factory=list)
    reliability_score: float = 0.0
    retrieved_at: datetime = Field(default_factory=datetime.now)
    objective_mapping: List[str] = Field(default_factory=list)

class KnowledgeBaseEntry(BaseModel):
    summary: str
    source: str
    confidence: float
    covered_objectives: List[str]
    supporting_evidence: str
    document: Optional[SourceDocument] = None

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
    contradicting_sources: List[str] = Field(default_factory=list)
    source_types: List[str] = Field(default_factory=list)
    confidence: float # 0-100
    evidence_strength: str # Strong, Moderate, Weak
    strength_justification: str = ""
    agreement_score: float # 0-100
    publication_dates: List[str] = Field(default_factory=list)
    support_count: int = 0
    confirmation_count: int = 0
    primary_evidence: bool = False

class EvidenceGraph(BaseModel):
    items: List[EvidenceItem] = Field(default_factory=list)

class ConfidenceBreakdown(BaseModel):
    overall: float = 0.0
    coverage: float = 0.0
    evidence_strength: float = 0.0
    source_diversity: float = 0.0
    agreement: float = 0.0
    extraction_quality: float = 0.0
    missing_evidence_penalty: float = 0.0
    contradiction_penalty: float = 0.0
    source_quality: float = 0.0
    freshness: float = 0.0
    search_exhaustiveness: float = 0.0
    explanation: str = ""
    status: str = "Active"
    reason: str = ""

class ResearchGap(BaseModel):
    topic: str
    reason_missing: str = ""
    suggested_queries: List[str]
    recommended_authoritative_sources: List[str] = Field(default_factory=list)
    estimated_confidence_improvement: float = 0.0

class ReasoningResult(BaseModel):
    objective_states: List[ObjectiveState] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    follow_up_queries: List[str] = Field(default_factory=list)
    continue_research: bool
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    gaps: List[ResearchGap] = Field(default_factory=list)

class ProfilingStats(BaseModel):
    stages: Dict[str, float] = Field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0
    cache_hits: int = 0
    retry_count: int = 0
    http_latency: float = 0.0
    llm_latency: float = 0.0
    estimated_cost_usd: float = 0.0
    provider_failures: int = 0

class SourceV2Info(BaseModel):
    url: str
    title: str = ""
    score: float
    tier: int = 5
    type: str
    rejection_reason: Optional[str] = None

SourceV2Info.model_rebuild()

class SearchHealth(BaseModel):
    success_rate: float = 1.0
    timeouts: int = 0
    errors_403: int = 0
    errors_429: int = 0
    captcha_count: int = 0
    avg_latency: float = 0.0

class ResearchState(BaseModel):
    report_id: str = ""
    query: str
    plan: Optional[ResearchPlan] = None
    iterations: int = 0
    urls_found: int = 0
    urls_rejected: List[SourceV2Info] = Field(default_factory=list)
    visited_urls: List[str] = Field(default_factory=list)
    failed_fetches: List[str] = Field(default_factory=list)
    successful_downloads: int = 0
    failed_downloads: int = 0
    successful_extractions: int = 0
    successful_summaries: int = 0
    fallback_summaries_used: int = 0
    sources_collected: List[str] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    evidence_graph: EvidenceGraph = Field(default_factory=EvidenceGraph)
    objective_states: Dict[str, ObjectiveState] = Field(default_factory=dict)
    confidence_evolution: List[float] = Field(default_factory=list)
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    gaps: List[ResearchGap] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.now)
    profiling: ProfilingStats = Field(default_factory=ProfilingStats)
    knowledge_base: List[KnowledgeBaseEntry] = Field(default_factory=list)
    confidence_score: float = 0.0
    search_health: Dict[str, SearchHealth] = Field(default_factory=dict)
    follow_up_queries: List[str] = Field(default_factory=list)
    report_status: str = "not_started"

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
    recommendations: List[str] = Field(default_factory=list)
    practical_applications: List[str] = Field(default_factory=list)
    decision_maker_notes: str = ""
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
    retry_rate: float = 0.0
    llm_latency_avg: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
