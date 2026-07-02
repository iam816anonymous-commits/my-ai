import logging
import re
from typing import List, Dict
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ReasoningResult, ArticleSummary, ResearchPlan, KnowledgeBaseEntry
import json

logger = logging.getLogger(__name__)

def calculate_confidence(state_data: Dict) -> float:
    """
    Calculates a realistic confidence score (0-100).
    """
    coverage = state_data.get("objective_coverage", {})
    if not coverage:
        return 0.0

    avg_coverage = sum(coverage.values()) / len(coverage)

    successful_summaries = state_data.get("successful_summaries", 0)
    urls_found = state_data.get("urls_found", 1)
    source_ratio = min(successful_summaries / max(urls_found, 1), 1.0)

    contradictions = len(state_data.get("contradictions", []))
    agreement_penalty = max(0, 100 - (contradictions * 10))

    # Weighting: 60% coverage, 20% source ratio, 20% agreement
    score = (avg_coverage * 0.6) + (source_ratio * 100 * 0.2) + (agreement_penalty * 0.2)

    return round(max(0, min(score, 100)), 2)

def evaluate_research(
    query: str,
    plan: ResearchPlan,
    summaries: List[ArticleSummary],
    llm_client: LLMClient,
    current_iteration: int
) -> ReasoningResult:
    """
    Analyzes research progress with analytical depth.
    """
    knowledge_snapshot = "\n".join([f"Source: {s.url}\nSummary: {s.summary[:300]}..." for s in summaries])

    prompt = f"""
    Topic: {plan.topic}
    Objectives: {plan.objectives}
    Current Evidence: {knowledge_snapshot[:6000]}

    Task: Critically evaluate the information collected.
    1. Identify which objectives are fully covered (>90%).
    2. Identify missing evidence or contradictions.
    3. Generate 3-5 high-precision follow-up queries if needed.

    Return JSON:
    {{
        "completed_objectives": ["obj1"],
        "missing_objectives": ["obj2"],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "confidence": 0-100,
        "objective_coverage": {{ "objective_text": 0.0 }},
        "follow_up_queries": [],
        "continue_research": bool
    }}

    Set continue_research to false ONLY if all objectives > 90% or no new info possible.
    """
    sys_prompt = "You are a professional research analyst. Be critical and precise. Output valid JSON."

    try:
        data = llm_client.get_json(prompt, sys_prompt)

        # Validation and normalization
        coverage = data.get("objective_coverage", {})
        for obj in plan.objectives:
            if obj not in coverage:
                coverage[obj] = 0.0
        data["objective_coverage"] = coverage

        # Override continue_research if objectives are clearly missing and we have iterations left
        if any(v < 90 for v in coverage.values()) and current_iteration < 3:
            data["continue_research"] = True

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
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
    """Adds new evidence to knowledge base."""
    for s in new_summaries:
        covered = []
        summary_lower = s.summary.lower()
        for obj in plan.objectives:
            # Check for multiple keywords from objective
            keywords = [w.lower() for w in re.findall(r'\w+', obj) if len(w) > 3]
            match_count = sum(1 for k in keywords if k in summary_lower)
            if match_count >= 1:
                covered.append(obj)

        kb.append(KnowledgeBaseEntry(
            summary=s.summary,
            source=s.url,
            confidence=0.85,
            covered_objectives=covered,
            supporting_evidence=s.summary[:200]
        ))
    return kb
