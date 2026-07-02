import logging
import re
from typing import List, Dict, Any
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ReasoningResult, ArticleSummary, ResearchPlan, KnowledgeBaseEntry, EvidenceItem, EvidenceGraph

logger = logging.getLogger(__name__)

def calculate_confidence(state_data: Dict) -> float:
    """
    Calculates a realistic confidence score (0-100) based on multiple factors.
    """
    coverage_dict = state_data.get("objective_coverage", {})
    if not coverage_dict:
        return 0.0

    # 1. Average Coverage (60%)
    avg_coverage = sum(coverage_dict.values()) / len(coverage_dict)

    # 2. Source Quality & Density (20%)
    summaries = state_data.get("summaries", [])
    source_count = len(summaries)
    source_score = min(source_count / 8.0, 1.0) * 100

    # 3. Evidence Agreement & Contradictions (20%)
    contradictions = state_data.get("contradictions", [])
    agreement_score = max(0, 100 - (len(contradictions) * 5))

    # Final Weighted Score
    final_score = (avg_coverage * 0.6) + (source_score * 0.2) + (agreement_score * 0.2)

    return round(max(0, min(final_score, 100)), 2)

def evaluate_research(
    query: str,
    plan: ResearchPlan,
    summaries: List[ArticleSummary],
    llm_client: LLMClient,
    current_iteration: int
) -> ReasoningResult:
    """
    Analytical evaluation of evidence and coverage.
    Ensures coverage is treated as 0-100.
    """
    evidence_snapshot = "\n".join([f"SOURCE: {s.url}\nCONTENT: {s.summary[:400]}..." for s in summaries])

    prompt = f"""
    TOPIC: {plan.topic}
    INTENT: {plan.intent}
    OBJECTIVES: {plan.objectives}
    EVIDENCE COLLECTED:
    {evidence_snapshot[:8000]}

    TASK: Analyze the evidence against research objectives.
    1. Update coverage (0-100%) for each objective.
    2. Identify core claims for the Evidence Graph.
    3. Identify contradictions.
    4. Highlight claims with weak evidence.
    5. Generate follow-up queries if coverage is below 90% and iterations < 3.

    RETURN JSON:
    {{
        "completed_objectives": [],
        "missing_objectives": [],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "confidence": 0-100,
        "objective_coverage": {{ "exact_objective_text": 0-100 }},
        "evidence_items": [{{ "claim": "", "supporting_sources": [url], "confidence": 0-100, "evidence_strength": "Strong/Moderate/Weak", "agreement_score": 0-100 }}],
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """
    sys_prompt = "You are a professional evidence analyst. Provide rigorous evaluations. Weak evidence must be identified."

    try:
        data = llm_client.get_json(prompt, sys_prompt)

        # Validation and normalization
        coverage = data.get("objective_coverage", {})
        for obj in plan.objectives:
            val = coverage.get(obj, 0.0)
            if val < 1.0 and val > 0:
                val = val * 100
            coverage[obj] = min(max(val, 0.0), 100.0)
        data["objective_coverage"] = coverage

        if any(v < 90 for v in coverage.values()) and current_iteration < 3:
            data["continue_research"] = True
        else:
            data["continue_research"] = False

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning evaluation failed: {e}")
        return ReasoningResult(
            completed_objectives=[],
            missing_objectives=plan.objectives,
            confidence=0,
            objective_coverage={obj: 0.0 for obj in plan.objectives},
            continue_research=False
        )

def update_knowledge_base(
    kb: List[KnowledgeBaseEntry],
    new_summaries: List[ArticleSummary],
    plan: ResearchPlan
) -> List[KnowledgeBaseEntry]:
    """Adds evidence to in-memory store."""
    for s in new_summaries:
        kb.append(KnowledgeBaseEntry(
            summary=s.summary,
            source=s.url,
            confidence=0.9,
            covered_objectives=[obj for obj in plan.objectives if any(k in s.summary.lower() for k in re.findall(r'\w+', obj.lower()) if len(k) > 4)],
            supporting_evidence=s.summary[:300]
        ))
    return kb
