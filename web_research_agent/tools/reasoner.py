import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ReasoningResult, ArticleSummary, ResearchPlan,
    KnowledgeBaseEntry, EvidenceItem, ConfidenceBreakdown, ResearchGap
)

logger = logging.getLogger(__name__)

def calculate_explainable_confidence(state_data: Dict) -> ConfidenceBreakdown:
    """Calculates detailed weighted confidence breakdown."""
    coverage_dict = state_data.get("objective_coverage", {})
    avg_coverage = sum(coverage_dict.values()) / len(coverage_dict) if coverage_dict else 0

    summaries = state_data.get("summaries", [])
    unique_domains = set(urlparse(s.get("url", "")).netloc for s in summaries if s.get("url"))
    source_diversity = min(len(unique_domains) / 6.0, 1.0) * 100

    avg_quality = sum(s.get("quality_score", 50) for s in summaries) / len(summaries) if summaries else 0
    contradictions = len(state_data.get("contradictions", []))
    agreement_score = max(0, 100 - (contradictions * 10))

    # Weights: 40% Coverage, 25% Strength, 20% Diversity, 15% Agreement
    overall = (avg_coverage * 0.40) + (avg_quality * 0.25) + (source_diversity * 0.20) + (agreement_score * 0.15)

    return ConfidenceBreakdown(
        overall=round(overall, 2),
        coverage=round(avg_coverage, 2),
        evidence_strength=round(avg_quality, 2),
        source_diversity=round(source_diversity, 2),
        agreement=round(agreement_score, 2),
        extraction_quality=98.0,
        missing_evidence_penalty=round((100 - avg_coverage) * 0.4, 2),
        contradiction_penalty=float(contradictions * 5)
    )

def evaluate_research(query: str, plan: ResearchPlan, summaries: List[ArticleSummary], llm_client: LLMClient, current_iteration: int) -> ReasoningResult:
    """Rigorous analyst evaluation of evidence and gaps."""
    evidence_snapshot = "\n".join([f"SOURCE [{i}]: {s.url} ({s.source_type}, Tier {s.source_tier})\nSUMMARY: {s.summary[:400]}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent}
    OBJECTIVES: {plan.objectives}
    COLLECTED EVIDENCE:
    {evidence_snapshot[:10000]}

    TASK: Critically analyze the evidence.
    1. Update coverage (0-100) per objective.
    2. Build an Evidence Graph of claims.
    3. JUSTIFY evidence strength (Strong/Moderate/Weak) based on Source Tier, Support Count, and Agreement.
    4. Detail Gaps: Why missing? Sugged authoritative sources and queries.

    RETURN JSON:
    {{
        "completed_objectives": [],
        "missing_objectives": [],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "objective_coverage": {{ "exact_objective": 0-100 }},
        "evidence_items": [{{
            "claim": "",
            "supporting_sources": [],
            "source_types": [],
            "confidence": 0-100,
            "evidence_strength": "Strong/Moderate/Weak",
            "strength_justification": "Why? (e.g., Tier-1 sources + high agreement)",
            "agreement_score": 0-100,
            "publication_dates": []
        }}],
        "gaps": [{{
            "topic": "",
            "reason_missing": "",
            "suggested_queries": [],
            "recommended_authoritative_sources": [],
            "estimated_confidence_improvement": 0.0
        }}],
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """
    try:
        data = llm_client.get_json(prompt, "Evidence analyst. JSON only.")
        # Norm coverage
        coverage = data.get("objective_coverage", {})
        for obj in plan.objectives:
            val = coverage.get(obj, 0.0)
            if 0 < val < 1: val *= 100
            coverage[obj] = min(max(val, 0.0), 100.0)
        data["objective_coverage"] = coverage
        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning error: {e}")
        return ReasoningResult(completed_objectives=[], missing_objectives=plan.objectives, objective_coverage={o:0.0 for o in plan.objectives}, continue_research=False)

def update_knowledge_base(kb: List[KnowledgeBaseEntry], new_summaries: List[ArticleSummary], plan: ResearchPlan) -> List[KnowledgeBaseEntry]:
    for s in new_summaries:
        kb.append(KnowledgeBaseEntry(
            summary=s.summary, source=s.url, confidence=0.9,
            covered_objectives=[], supporting_evidence=s.summary[:200]
        ))
    return kb
