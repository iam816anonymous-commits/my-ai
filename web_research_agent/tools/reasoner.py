import logging
import re
import time
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ReasoningResult, ArticleSummary, ResearchPlan,
    KnowledgeBaseEntry, EvidenceItem, ConfidenceBreakdown, ResearchGap, ObjectiveState, ObjectiveStatus, PipelineResult
)

logger = logging.getLogger(__name__)

def calculate_production_confidence(state_data: Dict) -> ConfidenceBreakdown:
    """Redesigned strictly signal-based confidence engine."""
    obj_states = state_data.get("objective_states", {})
    summaries = state_data.get("summaries", [])
    contradictions = state_data.get("contradictions", [])

    if not summaries or not obj_states:
        return ConfidenceBreakdown(overall=0.0, status="Insufficient Data", reason="Evidence or Objectives missing")

    # 1. Coverage (40%) - Measurable objective completion
    avg_coverage = sum(o.get("coverage", 0) for o in obj_states.values()) / len(obj_states)

    # 2. Source Authority & Diversity (20%)
    unique_domains = set(urlparse(s.get("url", "")).netloc for s in summaries if s.get("url"))
    domain_diversity = min(len(unique_domains) / 6.0, 1.0) * 100 # Target 6+ domains

    # Tier 1 & 2 weight
    high_authority_count = len([s for s in summaries if s.get("source_tier", 5) <= 2])
    authority_score = min(high_authority_count / 4.0, 1.0) * 100 # Target 4+ high-authority sources

    # 3. Evidence Density & Agreement (25%)
    evidence_count = state_data.get("evidence_count", len(summaries))
    density_score = min(evidence_count / 15.0, 1.0) * 100 # Target 15+ evidence items

    # Agreement (deduct for contradictions)
    agreement_score = max(0, 100 - (len(contradictions) * 15))

    # 4. Search Exhaustiveness (15%)
    iterations = state_data.get("iterations", 1)
    exhaustiveness = min((iterations / 3.0), 1.0) * 100 # Target 3 cycles

    # Weighted Sum
    overall = (avg_coverage * 0.40) + \
              (authority_score * 0.15) + \
              (domain_diversity * 0.10) + \
              (density_score * 0.15) + \
              (agreement_score * 0.10) + \
              (exhaustiveness * 0.10)

    # Hard Cap: No evidence => Zero confidence
    if not summaries or avg_coverage < 5:
        overall = 0.0

    explanation = (
        f"Confidence {overall:.1f}/100. Signal breakdown: Coverage({avg_coverage:.0f}%), "
        f"Authority({authority_score:.0f}%), Diversity({domain_diversity:.0f}%), "
        f"Density({density_score:.0f}%), Agreement({agreement_score:.0f}%)."
    )

    return ConfidenceBreakdown(
        overall=round(overall, 2),
        coverage=round(avg_coverage, 2),
        evidence_strength=round(density_score, 2),
        source_diversity=round(domain_diversity, 2),
        agreement=round(agreement_score, 2),
        source_quality=round(authority_score, 2),
        search_exhaustiveness=round(exhaustiveness, 2),
        explanation=explanation,
        status="Finalized"
    )

def calculate_explainable_confidence(*args, **kwargs):
    """Backward compatibility wrapper for calculate_production_confidence."""
    return calculate_production_confidence(*args, **kwargs)

def evaluate_research(query: str, plan: ResearchPlan, summaries: List[ArticleSummary], llm_client: LLMClient, current_iteration: int, urls_found: int = 0, previous_states: Dict[str, ObjectiveState] = None) -> PipelineResult[ReasoningResult]:
    """Adaptive reasoning engine with objective state lifecycle."""
    start_time = time.time()
    evidence_snapshot = "\n".join([f"SOURCE: {s.url}\nTier: {s.source_tier}\nCONTENT: {s.summary[:800]}" for s in summaries])
    state_snapshot = "\n".join([f"- {o}: {s.status} ({s.coverage}%)" for o, s in (previous_states or {}).items()])

    prompt = f"""
    TOPIC: {plan.topic} | Query: {query}
    Current Iteration: {current_iteration}

    OBJECTIVES: {plan.objectives}
    PREVIOUS STATES:
    {state_snapshot}

    EVIDENCE:
    {evidence_snapshot[:20000]}

    TASK:
    1. Evaluate each objective. Update Status: NOT_STARTED, SEARCHING, PARTIAL, COMPLETE, FAILED, BLOCKED.
    2. Calculate coverage (0-100) based on hard evidence.
    3. Identify contradictions between sources.
    4. Detect Gaps: If an objective is not COMPLETE, explain why and generate high-precision follow-up queries.

    JSON: {{
        "objective_states": [{{
            "objective": "", "status": "STATUS", "coverage": 0-100,
            "evidence_count": 0, "number_of_sources": 0, "missing_evidence": ""
        }}],
        "contradictions": [],
        "evidence_items": [],
        "gaps": [],
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """

    try:
        data = llm_client.get_json(prompt, "Expert Research Analyst. JSON only.")

        res_states = []
        total_evidence = 0
        for obj_data in data.get("objective_states", []):
            obj_name = obj_data["objective"]
            prev = previous_states.get(obj_name) if previous_states else None
            status_str = obj_data.get("status", "SEARCHING").upper()
            status = ObjectiveStatus[status_str] if status_str in ObjectiveStatus.__members__ else ObjectiveStatus.SEARCHING

            attempts = (prev.search_attempts if prev else 0) + 1
            total_evidence += obj_data.get("evidence_count", 0)

            res_states.append(ObjectiveState(
                objective=obj_name,
                status=status,
                coverage=obj_data.get("coverage", 0.0),
                evidence_count=obj_data.get("evidence_count", 0),
                number_of_sources=obj_data.get("number_of_sources", 0),
                missing_evidence=obj_data.get("missing_evidence", ""),
                search_attempts=attempts,
                last_update_iteration=current_iteration
            ))

        confidence = calculate_production_confidence({
            "objective_states": {o.objective: o.model_dump() for o in res_states},
            "summaries": [s.model_dump() for s in summaries],
            "contradictions": data.get("contradictions", []),
            "evidence_count": total_evidence,
            "iterations": current_iteration
        })

        result = ReasoningResult(
            objective_states=res_states,
            contradictions=data.get("contradictions", []),
            evidence_items=data.get("evidence_items", []),
            gaps=data.get("gaps", []),
            follow_up_queries=data.get("follow_up_queries", []),
            continue_research=data.get("continue_research", True) and current_iteration < 3,
            confidence_breakdown=confidence
        )

        return PipelineResult(success=True, payload=result, stage="reasoning", timing=time.time() - start_time)
    except Exception as e:
        return PipelineResult(success=False, errors=[str(e)], stage="reasoning", timing=time.time() - start_time)

from web_research_agent.models.schemas import SourceDocument
import hashlib

def update_knowledge_base(kb: List[KnowledgeBaseEntry], new_summaries: List[ArticleSummary], plan: ResearchPlan, valid_texts: Dict[str, str]) -> List[KnowledgeBaseEntry]:
    """Ensures knowledge accumulates and tracks objective mapping with rich documents."""
    for s in new_summaries:
        if not any(k.source == s.url for k in kb):
            # Create rich SourceDocument (Module 8)
            doc_id = hashlib.md5(s.url.encode()).hexdigest()[:10]
            doc = SourceDocument(
                id=doc_id,
                url=s.url,
                title=s.title or "Untitled",
                authority_score=s.quality_score,
                domain=urlparse(s.url).netloc,
                clean_text=valid_texts.get(s.url, ""),
                summary=s.summary,
                reliability_score=1.0 if s.source_tier <= 2 else 0.7
            )

            kb.append(KnowledgeBaseEntry(
                summary=s.summary,
                source=s.url,
                confidence=1.0,
                covered_objectives=[],
                supporting_evidence=s.summary[:300],
                document=doc
            ))
    return kb
