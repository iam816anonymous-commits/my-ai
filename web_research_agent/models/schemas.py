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

class Contradiction(BaseModel):
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    explanation: Optional[str] = None

class EvidenceItem(BaseModel):
    claim: str
    supporting_sources: List[str]
    confidence: float # 0-100
    evidence_strength: str # Strong, Medium, Weak
    agreement_score: float # 0-100

class EvidenceGraph(BaseModel):
    items: List[EvidenceItem] = Field(default_factory=list)

class ReasoningResult(BaseModel):
    completed_objectives: List[str]
    missing_objectives: List[str]
    contradictions: List[Contradiction] = Field(default_factory=list)
    confidence: float # 0-100
    objective_coverage: Dict[str, float] # objective: coverage % (0-100)
    follow_up_queries: List[str] = Field(default_factory=list)
    continue_research: bool
    evidence_items: List[EvidenceItem] = Field(default_factory=list)

class KnowledgeBaseEntry(BaseModel):
    summary: str
    source: str
    confidence: float
    covered_objectives: List[str]
    supporting_evidence: str

class SelfEvaluation(BaseModel):
    coverage_score: float
    evidence_score: float
    readability_score: float
    citation_quality: float
    objectivity: float
    bias_risk: float
    novel_insights: float
    overall_grade: str # A, B, C, etc.
    justification: str

class ProfilingStats(BaseModel):
    slowest_functions: Dict[str, float] = Field(default_factory=dict)
    prompt_sizes: List[int] = Field(default_factory=list)
    response_sizes: List[int] = Field(default_factory=list)
    download_times: List[float] = Field(default_factory=list)
    extraction_times: List[float] = Field(default_factory=list)

class SourceQualityStats(BaseModel):
    type_counts: Dict[str, int] = Field(default_factory=dict)
    average_score: float = 0.0

class ResearchState(BaseModel):
    query: str
    plan: Optional[ResearchPlan] = None
    iterations: int = 0
    urls_found: int = 0
    urls_filtered: int = 0
    urls_processed: int = 0
    successful_downloads: int = 0
    successful_extractions: int = 0
    successful_summaries: int = 0
    fallback_summaries_used: int = 0
    failed_pages: List[Dict[str, str]] = Field(default_factory=list)
    sources_collected: List[str] = Field(default_factory=list)
    knowledge_base: List[KnowledgeBaseEntry] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    evidence_graph: EvidenceGraph = Field(default_factory=EvidenceGraph)
    objective_coverage: Dict[str, float] = Field(default_factory=dict)
    follow_up_queries: List[str] = Field(default_factory=list)
    report_status: str = "not_started"
    confidence_score: float = 0.0
    start_time: datetime = Field(default_factory=datetime.now)
    profiling: ProfilingStats = Field(default_factory=ProfilingStats)
    source_stats: SourceQualityStats = Field(default_factory=SourceQualityStats)

class ResearchReport(BaseModel):
    title: str
    executive_summary: str
    key_findings: List[str]
    background: str
    detailed_analysis: str
    supporting_evidence: List[EvidenceItem]
    contradictions: List[Contradiction]
    limitations: List[str]
    confidence_assessment: str
    references: List[str]
    self_evaluation: Optional[SelfEvaluation] = None

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
