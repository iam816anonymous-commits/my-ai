import logging
import re
from typing import List, Dict, Any
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ReasoningResult, ArticleSummary, ResearchPlan,
    EvidenceItem, ConfidenceBreakdown, ResearchGap
)

logger = logging.getLogger(__name__)

def calculate_explainable_confidence(state_data: Dict) -> ConfidenceBreakdown:
    """
    Calculates detailed confidence breakdown.
    """
    coverage_dict = state_data.get("objective_coverage", {})
    avg_coverage = sum(coverage_dict.values()) / len(coverage_dict) if coverage_dict else 0

    summaries = state_data.get("summaries", [])
    source_diversity = min(len(set(re.search(r'://([^/]+)', s.get("url", "")).group(1) for s in summaries if "://" in s.get("url", ""))) / 6.0, 1.0) * 100 if summaries else 0

    # Weights for evidence strength (simulation for now based on quality scores)
    avg_source_quality = sum(s.get("quality_score", 50) for s in summaries) / len(summaries) if summaries else 0

    contradictions = state_data.get("contradictions", [])
    contradiction_penalty = len(contradictions) * 5

    missing_penalty = (100 - avg_coverage) * 0.5

    # Final components
    comp_coverage = avg_coverage
    comp_strength = avg_source_quality
    comp_diversity = source_diversity
    comp_agreement = max(0, 100 - contradiction_penalty)
    comp_extraction = 95.0 # Constant for now

    overall = (comp_coverage * 0.4) + (comp_strength * 0.2) + (comp_diversity * 0.2) + (comp_agreement * 0.2)
    overall = max(0, min(overall, 100))

    return ConfidenceBreakdown(
        overall=round(overall, 2),
        coverage=round(comp_coverage, 2),
        evidence_strength=round(comp_strength, 2),
        source_diversity=round(comp_diversity, 2),
        agreement=round(comp_agreement, 2),
        extraction_quality=comp_extraction,
        missing_evidence_penalty=round(missing_penalty, 2),
        contradiction_penalty=float(contradiction_penalty)
    )

def evaluate_research(
    query: str,
    plan: ResearchPlan,
    summaries: List[ArticleSummary],
    llm_client: LLMClient,
    current_iteration: int
) -> ReasoningResult:
    """
    Reasoning with gap detection and evidence mapping.
    """
    evidence_snapshot = "\n".join([f"SOURCE: {s.url}\nSUMMARY: {s.summary[:400]}" for s in summaries])

    prompt = f"""
    TOPIC: {plan.topic}
    INTENT: {plan.intent}
    OBJECTIVES: {plan.objectives}
    EVIDENCE:
    {evidence_snapshot[:8000]}

    TASK: Critically evaluate the state of research.
    1. Update coverage (0-100) per objective.
    2. Map key evidence items with source references.
    3. Detect research gaps and suggest specific follow-ups.

    RETURN JSON:
    {{
        "completed_objectives": [],
        "missing_objectives": [],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "objective_coverage": {{ "objective_text": 0-100 }},
        "evidence_items": [{{ "claim": "", "supporting_sources": [url], "confidence": 0-100, "evidence_strength": "Strong/Medium/Weak", "agreement_score": 0-100 }}],
        "gaps": [{{ "topic": "", "suggested_queries": [], "recommended_sources": [] }}],
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """
    sys_prompt = "Analytical reasoning engine. JSON output only. Be extremely thorough."

    try:
        data = llm_client.get_json(prompt, sys_prompt)

        # Coverage normalization
        coverage = data.get("objective_coverage", {})
        for obj in plan.objectives:
            if obj not in coverage: coverage[obj] = 0.0
        data["objective_coverage"] = coverage

        # Confidence breakdown logic is handled in the agent to include all state info

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning iteration failed: {e}")
        return ReasoningResult(
            completed_objectives=[],
            missing_objectives=plan.objectives,
            objective_coverage={obj: 0.0 for obj in plan.objectives},
            continue_research=False
        )
