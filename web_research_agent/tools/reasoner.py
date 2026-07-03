import logging
import re
from typing import List, Dict, Any
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ReasoningResult, ArticleSummary, ResearchPlan, KnowledgeBaseEntry, EvidenceItem, EvidenceGraph, ConfidenceBreakdown

logger = logging.getLogger(__name__)

def calculate_explainable_confidence(state_data: Dict) -> ConfidenceBreakdown:
    coverage_dict = state_data.get("objective_coverage", {})
    avg_coverage = sum(coverage_dict.values()) / len(coverage_dict) if coverage_dict else 0
    summaries = state_data.get("summaries", [])
    source_diversity = min(len(set(urlparse(s.get("url", "")).netloc for s in summaries)) / 6.0, 1.0) * 100 if summaries else 0
    avg_quality = sum(s.get("quality_score", 50) for s in summaries) / len(summaries) if summaries else 0
    contradiction_penalty = len(state_data.get("contradictions", [])) * 5

    overall = (avg_coverage * 0.4) + (avg_quality * 0.2) + (source_diversity * 0.2) + (max(0, 100-contradiction_penalty) * 0.2)
    return ConfidenceBreakdown(
        overall=round(overall, 2), coverage=round(avg_coverage, 2), evidence_strength=round(avg_quality, 2),
        source_diversity=round(source_diversity, 2), agreement=round(max(0, 100-contradiction_penalty), 2),
        extraction_quality=95.0, missing_evidence_penalty=round((100-avg_coverage)*0.5, 2), contradiction_penalty=float(contradiction_penalty)
    )

def evaluate_research(query: str, plan: ResearchPlan, summaries: List[ArticleSummary], llm_client: LLMClient, current_iteration: int) -> ReasoningResult:
    evidence_snapshot = "\n".join([f"SOURCE [{i}]: {s.url} ({s.source_type})\nSUMMARY: {s.summary[:400]}" for i, s in enumerate(summaries)])
    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent} | OBJECTIVES: {plan.objectives}
    EVIDENCE: {evidence_snapshot[:8000]}

    TASK: Analytical Evaluation.
    1. Update coverage (0-100) per objective.
    2. Map Evidence items. EXPLAIN why strength is Strong/Weak based on Source Type and Agreement.
    3. Detail research gaps with suggested authoritative sources and queries.

    JSON: {{
        "completed_objectives": [], "missing_objectives": [],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "objective_coverage": {{ "exact_objective": 0-100 }},
        "evidence_items": [{{ "claim": "", "supporting_sources": [], "confidence": 0-100, "evidence_strength": "Strong/Medium/Weak", "strength_justification": "", "agreement_score": 0-100 }}],
        "gaps": [{{ "topic": "", "reason_missing": "", "suggested_queries": [], "recommended_authoritative_sources": [], "estimated_confidence_improvement": 0.0 }}],
        "follow_up_queries": [], "continue_research": bool
    }}
    """
    try:
        data = llm_client.get_json(prompt, "Evidence analyst. JSON only.")
        coverage = data.get("objective_coverage", {})
        for obj in plan.objectives:
            val = coverage.get(obj, 0.0)
            if 0 < val < 1: val *= 100
            coverage[obj] = min(max(val, 0.0), 100.0)
        data["objective_coverage"] = coverage
        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning fail: {e}")
        return ReasoningResult(completed_objectives=[], missing_objectives=plan.objectives, objective_coverage={o:0.0 for o in plan.objectives}, continue_research=False)

def update_knowledge_base(kb: List[KnowledgeBaseEntry], new_summaries: List[ArticleSummary], plan: ResearchPlan) -> List[KnowledgeBaseEntry]:
    for s in new_summaries:
        kb.append(KnowledgeBaseEntry(summary=s.summary, source=s.url, confidence=0.9, covered_objectives=[], supporting_evidence=s.summary[:200]))
    return kb
from urllib.parse import urlparse
