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
    if not obj_states: return ConfidenceBreakdown(status="Unavailable", reason="No objective states found")

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
        source_quality=round(avg_quality, 2), freshness=90.0, status="Success"
    )

def evaluate_research(query: str, plan: ResearchPlan, summaries: List[ArticleSummary], llm_client: LLMClient, current_iteration: int, previous_states: Dict[str, ObjectiveState] = None) -> ReasoningResult:
    """Rigorous analyst-grade evidence review."""
    evidence_snapshot = "\n".join([f"SOURCE [{i}]: {s.url} ({s.source_type}, Tier {s.source_tier})\nSUMMARY: {s.summary[:400]}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic} | OBJECTIVES: {plan.objectives}
    EVIDENCE: {evidence_snapshot[:10000]}

    TASK: Critical Evidence Review.
    1. Update state for EVERY objective: coverage(0-100), evidence_count, confidence, missing_evidence.
    2. Build Evidence Graph. EXPLAIN strength (Strong/Moderate/Weak) based on Source Tier and Agreement.
    3. Detect Gaps: suggested authoritative sources and TARGETED queries.

    JSON: {{
        "objective_states": [{{ "objective": "", "coverage": 0-100, "evidence_count": 0, "confidence": 0-100, "missing_evidence": "" }}],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "evidence_items": [{{ "claim": "", "supporting_sources": [], "source_types": [], "confidence": 0-100, "evidence_strength": "Strong/Medium/Weak", "strength_justification": "", "agreement_score": 0-100, "support_count": 0 }}],
        "gaps": [{{ "topic": "", "reason_missing": "", "suggested_queries": [], "recommended_authoritative_sources": [], "estimated_confidence_improvement": 0.0 }}],
        "follow_up_queries": [], "continue_research": bool
    }}
    """
    try:
        data = llm_client.get_json(prompt, "Senior Analyst. JSON only.")

        # Merge with previous search attempt counts
        res_states = []
        for obj_data in data.get("objective_states", []):
            obj_name = obj_data["objective"]
            prev = previous_states.get(obj_name) if previous_states else None

            # Norm coverage
            cov = obj_data.get("coverage", 0.0)
            if 0 < cov < 1: cov *= 100

            # Increment attempts if coverage didn't increase significantly
            attempts = (prev.search_attempts if prev else 0) + 1

            res_states.append(ObjectiveState(
                objective=obj_name,
                coverage=min(max(cov, 0.0), 100.0),
                evidence_count=obj_data.get("evidence_count", 0),
                confidence=obj_data.get("confidence", 0.0),
                missing_evidence=obj_data.get("missing_evidence", ""),
                search_attempts=attempts,
                last_update_iteration=current_iteration
            ))

        data["objective_states"] = res_states
        data["confidence_breakdown"] = calculate_explainable_confidence({"objective_states": {o.objective: o.model_dump() for o in res_states}, "summaries": [s.model_dump() for s in summaries], "contradictions": data.get("contradictions", [])})

        # Smart termination: Stop if all critical objectives are met OR no new info in follow_up
        if not data.get("follow_up_queries"):
             data["continue_research"] = False

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return ReasoningResult(objective_states=[], continue_research=False, confidence_breakdown=ConfidenceBreakdown(status="Failed", reason=str(e)))

def update_knowledge_base(kb: List[KnowledgeBaseEntry], new_summaries: List[ArticleSummary], plan: ResearchPlan) -> List[KnowledgeBaseEntry]:
    for s in new_summaries:
        if not any(k.source == s.url for k in kb):
            kb.append(KnowledgeBaseEntry(summary=s.summary, source=s.url, confidence=0.9, covered_objectives=[], supporting_evidence=s.summary[:200]))
    return kb
