import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ReasoningResult, ArticleSummary, ResearchPlan,
    KnowledgeBaseEntry, EvidenceItem, ConfidenceBreakdown, ResearchGap, ObjectiveState
)

logger = logging.getLogger(__name__)

def calculate_explainable_confidence(state_data: Dict) -> ConfidenceBreakdown:
    obj_states = state_data.get("objective_states", {})
    if not obj_states: return ConfidenceBreakdown(overall=0, coverage=0, evidence_strength=0, source_diversity=0, agreement=0, extraction_quality=0, missing_evidence_penalty=0, contradiction_penalty=0)

    avg_coverage = sum(o.get("coverage", 0) for o in obj_states.values()) / len(obj_states)

    summaries = state_data.get("summaries", [])
    unique_domains = set(urlparse(s.get("url", "")).netloc for s in summaries if s.get("url"))
    source_diversity = min(len(unique_domains) / 6.0, 1.0) * 100
    avg_quality = sum(s.get("quality_score", 50) for s in summaries) / max(len(summaries), 1)

    contradictions = len(state_data.get("contradictions", []))
    agreement_score = max(0, 100 - (contradictions * 10))

    overall = (avg_coverage * 0.40) + (avg_quality * 0.25) + (source_diversity * 0.20) + (agreement_score * 0.15)
    return ConfidenceBreakdown(
        overall=round(overall, 2), coverage=round(avg_coverage, 2), evidence_strength=round(avg_quality, 2),
        source_diversity=round(source_diversity, 2), agreement=round(agreement_score, 2),
        extraction_quality=98.0, missing_evidence_penalty=round((100-avg_coverage)*0.4, 2), contradiction_penalty=float(contradictions * 5),
        source_quality=round(avg_quality, 2), freshness=90.0
    )

def evaluate_research(query: str, plan: ResearchPlan, summaries: List[ArticleSummary], llm_client: LLMClient, current_iteration: int) -> ReasoningResult:
    evidence_snapshot = "\n".join([f"SOURCE [{i}]: {s.url} ({s.source_type}, Tier {s.source_tier})\nSUMMARY: {s.summary[:400]}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic} | OBJECTIVES: {plan.objectives}
    EVIDENCE: {evidence_snapshot[:10000]}

    TASK: Critical Evidence Review.
    1. Update ObjectiveState for EACH objective: coverage(0-100), evidence_count, confidence, missing_evidence.
    2. Build Evidence Graph. Explain WHY strength is Weak/Moderate/Strong.
    3. Detect Gaps: Why missing? Suggested targeted queries (e.g., "Specific Law regulation" vs "general regulation").

    JSON: {{
        "objective_states": [{{ "objective": "", "coverage": 0-100, "evidence_count": 0, "confidence": 0-100, "missing_evidence": "" }}],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "evidence_items": [{{ "claim": "", "supporting_sources": [], "source_types": [], "confidence": 0-100, "evidence_strength": "Strong/Medium/Weak", "strength_justification": "", "agreement_score": 0-100, "publication_dates": [], "support_count": 0 }}],
        "gaps": [{{ "topic": "", "reason_missing": "", "suggested_queries": [], "recommended_authoritative_sources": [], "estimated_confidence_improvement": 0.0 }}],
        "follow_up_queries": [], "continue_research": bool
    }}
    """
    try:
        data = llm_client.get_json(prompt, "Senior Evidence Reviewer. Output JSON.")

        # Norm coverage values (0-100)
        for obj_state in data.get("objective_states", []):
            cov = obj_state.get("coverage", 0.0)
            if 0 < cov < 1: obj_state["coverage"] = cov * 100
            obj_state["last_update_iteration"] = current_iteration

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return ReasoningResult(objective_states=[], continue_research=False)

def update_knowledge_base(kb: List[KnowledgeBaseEntry], new_summaries: List[ArticleSummary], plan: ResearchPlan) -> List[KnowledgeBaseEntry]:
    # Proper merging logic
    for s in new_summaries:
        if not any(k.source == s.url for k in kb):
            kb.append(KnowledgeBaseEntry(summary=s.summary, source=s.url, confidence=0.9, covered_objectives=[], supporting_evidence=s.summary[:200]))
    return kb
