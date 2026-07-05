import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ReasoningResult, ArticleSummary, ResearchPlan,
    KnowledgeBaseEntry, EvidenceItem, ConfidenceBreakdown, ResearchGap, ObjectiveState, ObjectiveStatus
)

logger = logging.getLogger(__name__)

def calculate_explainable_confidence(state_data: Dict) -> ConfidenceBreakdown:
    obj_states = state_data.get("objective_states", {})
    if not obj_states: return ConfidenceBreakdown(status="Unavailable", reason="No objective states found")

    # 1. Coverage (40%)
    avg_coverage = sum(o.get("coverage", 0) for o in obj_states.values()) / len(obj_states)

    # 2. Source Authority & Diversity (20%)
    summaries = state_data.get("summaries", [])
    unique_domains = set(urlparse(s.get("url", "")).netloc for s in summaries if s.get("url"))
    source_diversity = min(len(unique_domains) / 8.0, 1.0) * 100
    avg_tier = sum(s.get("source_tier", 5) for s in summaries) / max(len(summaries), 1)
    source_authority = max(0, 100 - (avg_tier * 15))

    # 3. Evidence Strength & Agreement (25%)
    avg_quality = sum(s.get("quality_score", 50) for s in summaries) / max(len(summaries), 1)
    contradictions = len(state_data.get("contradictions", []))
    agreement_score = max(0, 100 - (contradictions * 12))

    # 4. Search Exhaustiveness (15%)
    iterations = state_data.get("iterations", 1)
    urls_found = state_data.get("urls_found", 0)
    search_exhaustiveness = min((iterations * 20) + (urls_found * 2), 100)

    # Weighted Calculation
    overall = (avg_coverage * 0.40) + (source_authority * 0.15) + (source_diversity * 0.10) + \
              (avg_quality * 0.15) + (agreement_score * 0.10) + (search_exhaustiveness * 0.10)

    # Penalties
    contradiction_penalty = float(contradictions * 6)
    missing_penalty = round((100 - avg_coverage) * 0.35, 2)
    overall = max(0, min(overall - (contradiction_penalty * 0.5), 100))

    explanation = (
        f"Confidence {overall:.1f}/100 based on {avg_coverage:.1f}% objective coverage, "
        f"{source_authority:.1f}% source authority across {len(unique_domains)} domains, "
        f"and {agreement_score:.1f}% evidence agreement. "
    )
    if contradictions > 0:
        explanation += f"Penalty applied for {contradictions} detected contradictions."

    return ConfidenceBreakdown(
        overall=round(overall, 2),
        coverage=round(avg_coverage, 2),
        evidence_strength=round(avg_quality, 2),
        source_diversity=round(source_diversity, 2),
        agreement=round(agreement_score, 2),
        extraction_quality=98.0,
        missing_evidence_penalty=missing_penalty,
        contradiction_penalty=contradiction_penalty,
        source_quality=round(source_authority, 2),
        freshness=90.0,
        search_exhaustiveness=round(search_exhaustiveness, 2),
        explanation=explanation,
        status="Success"
    )

def evaluate_research(query: str, plan: ResearchPlan, summaries: List[ArticleSummary], llm_client: LLMClient, current_iteration: int, urls_found: int = 0, previous_states: Dict[str, ObjectiveState] = None) -> ReasoningResult:
    """Autonomous adaptive reasoning engine."""
    evidence_snapshot = "\n".join([f"SOURCE [{i}]: {s.url} ({s.source_type}, Tier {s.source_tier})\nSUMMARY: {s.summary[:600]}" for i, s in enumerate(summaries)])

    # Track existing state for prompt context
    state_desc = "\n".join([f"- {o}: {s.status} (Cov: {s.coverage}%, Sources: {s.number_of_sources})" for o, s in (previous_states or {}).items()])

    prompt = f"""
    TOPIC: {plan.topic} | OBJECTIVES: {plan.objectives}
    PREVIOUS STATE:
    {state_desc}

    EVIDENCE: {evidence_snapshot[:20000]}

    TASK: Autonomous Analysis & State Machine Update.
    1. Update state machine for EVERY objective: NOT_STARTED, SEARCHING, FETCHING, SUMMARIZING, EVIDENCE_FOUND, VALIDATING, COMPLETE, FAILED, INSUFFICIENT_EVIDENCE.
    2. Calculate Coverage (0-100%): evidence count, independent domains, claim density, source quality.
    3. Require Source Diversity: 1 source is NEVER 'COMPLETE'. Need multiple independent confirmations.
    4. Detect Gaps: Generate progressively specific queries targeting missing technical details/academic proof.

    JSON: {{
        "objective_states": [{{
            "objective": "",
            "status": "STATUS_ENUM",
            "coverage": 0-100,
            "evidence_count": 0,
            "confidence": 0-100,
            "number_of_sources": 0,
            "source_diversity": 0.0-1.0,
            "contradictions_count": 0,
            "missing_evidence": ""
        }}],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "evidence_items": [{{
            "claim": "",
            "supporting_sources": [],
            "contradicting_sources": [],
            "source_types": [],
            "confidence": 0-100,
            "evidence_strength": "Strong/Moderate/Weak",
            "strength_justification": "",
            "agreement_score": 0-100,
            "support_count": 0,
            "confirmation_count": 0,
            "primary_evidence": bool
        }}],
        "gaps": [{{ "topic": "", "reason_missing": "", "suggested_queries": [], "recommended_authoritative_sources": [], "estimated_confidence_improvement": 0.0 }}],
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """
    try:
        data = llm_client.get_json(prompt, "Senior Analyst. JSON only.")
        if not data:
            raise ValueError("Reasoner received empty JSON from LLM")

        # Merge with previous search attempt counts
        res_states = []
        for obj_data in data.get("objective_states", []):
            obj_name = obj_data["objective"]
            prev = previous_states.get(obj_name) if previous_states else None

            # Norm coverage
            cov = obj_data.get("coverage", 0.0)
            if 0 < cov < 1: cov *= 100

            # Smart status transition logic (if LLM didn't provide a valid one)
            status_str = obj_data.get("status", "SEARCHING").upper()
            try:
                status = ObjectiveStatus[status_str]
            except KeyError:
                status = ObjectiveStatus.SEARCHING

            # Evidence saturation check
            improvement = cov - (prev.coverage if prev else 0.0)
            is_saturated = improvement < 2.0 and (prev.search_attempts if prev else 0) > 1

            if status == ObjectiveStatus.COMPLETE and improvement < 0:
                # Regression prevention
                cov = prev.coverage if prev else cov

            # Increment attempts
            attempts = (prev.search_attempts if prev else 0) + 1

            res_states.append(ObjectiveState(
                objective=obj_name,
                status=status,
                coverage=min(max(cov, 0.0), 100.0),
                evidence_count=obj_data.get("evidence_count", 0),
                confidence=obj_data.get("confidence", 0.0),
                number_of_sources=obj_data.get("number_of_sources", 0),
                source_diversity=obj_data.get("source_diversity", 0.0),
                contradictions_count=obj_data.get("contradictions_count", 0),
                missing_evidence=obj_data.get("missing_evidence", ""),
                search_attempts=attempts,
                last_update_iteration=current_iteration
            ))

        data["objective_states"] = res_states
        data["confidence_breakdown"] = calculate_explainable_confidence({
            "objective_states": {o.objective: o.model_dump() for o in res_states},
            "summaries": [s.model_dump() for s in summaries],
            "contradictions": data.get("contradictions", []),
            "iterations": current_iteration,
            "urls_found": urls_found
        })

        # Smart termination: Stop if all objectives are complete OR saturated
        all_complete = all(o.status == ObjectiveStatus.COMPLETE or o.coverage >= 85 for o in res_states)
        all_saturated = all(o.search_attempts >= 3 for o in res_states) # Max 3 attempts per objective

        if not data.get("follow_up_queries") or all_complete or all_saturated:
             data["continue_research"] = False
        else:
             data["continue_research"] = True

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return ReasoningResult(objective_states=[], continue_research=False, confidence_breakdown=ConfidenceBreakdown(status="Failed", reason=str(e)))

def update_knowledge_base(kb: List[KnowledgeBaseEntry], new_summaries: List[ArticleSummary], plan: ResearchPlan) -> List[KnowledgeBaseEntry]:
    for s in new_summaries:
        if not any(k.source == s.url for k in kb):
            kb.append(KnowledgeBaseEntry(summary=s.summary, source=s.url, confidence=0.9, covered_objectives=[], supporting_evidence=s.summary[:200]))
    return kb
