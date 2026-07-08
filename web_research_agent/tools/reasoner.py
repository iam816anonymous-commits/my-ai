import logging
import re
import time
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ReasoningResult, ArticleSummary, ResearchPlan,
    KnowledgeBaseEntry, EvidenceItem, ConfidenceBreakdown, ResearchGap, ObjectiveState, ObjectiveStatus, PipelineResult, ConfidenceInput
)

logger = logging.getLogger(__name__)

def calculate_production_confidence(inp: ConfidenceInput) -> ConfidenceBreakdown:
    """Redesigned strictly signal-based confidence engine."""
    if not inp.summaries or not inp.objective_states:
        return ConfidenceBreakdown(overall=0.0, status="Insufficient Data", reason="Evidence or Objectives missing")

    # 1. Coverage (40%) - Measurable objective completion
    avg_coverage = sum(o.coverage for o in inp.objective_states) / len(inp.objective_states)

    # 2. Source Authority & Diversity (20%)
    unique_domains = set(urlparse(s.url).netloc for s in inp.summaries if s.url)
    domain_diversity = min(len(unique_domains) / 6.0, 1.0) * 100 # Target 6+ domains

    # Tier 1 & 2 weight
    high_authority_count = len([s for s in inp.summaries if s.source_tier <= 2])
    authority_score = min(high_authority_count / 4.0, 1.0) * 100 # Target 4+ high-authority sources

    # 3. Evidence Density & Agreement (25%)
    density_score = min(inp.evidence_count / 15.0, 1.0) * 100 # Target 15+ evidence items

    # Agreement (deduct for contradictions)
    agreement_score = max(0, 100 - (len(inp.contradictions) * 15))

    # 4. Search Exhaustiveness (15%)
    exhaustiveness = min((inp.iterations / 3.0), 1.0) * 100 # Target 3 cycles

    # Weighted Sum (Phase 6 - Ensuring 1.0 sum)
    overall = (avg_coverage * 0.35) + \
              (authority_score * 0.15) + \
              (domain_diversity * 0.10) + \
              (density_score * 0.15) + \
              (agreement_score * 0.15) + \
              (exhaustiveness * 0.10)

    # Hard Cap: No evidence => Zero confidence
    if not inp.summaries or avg_coverage < 5:
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
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """

    try:
        result = llm_client.get_json(prompt, "Expert Research Analyst. JSON only.", response_model=ReasoningResult)

        # Deterministic Post-processing (Phase 4)
        res_states = []
        total_evidence = 0
        evidence_topics = set()

        # 1. Map evidence items to topics for gap analysis
        for item in result.evidence_items:
            # Simple keyword extraction from claim
            words = set(re.findall(r'\w{4,}', item.claim.lower()))
            evidence_topics.update(words)

        for obj in result.objective_states:
            prev = previous_states.get(obj.objective) if previous_states else None
            obj.search_attempts = (prev.search_attempts if prev else 0) + 1
            obj.last_update_iteration = current_iteration
            total_evidence += obj.evidence_count
            res_states.append(obj)

        result.objective_states = res_states

        # 2. Deterministic Gap Analysis (Phase 4)
        result.gaps = []
        for obj in res_states:
            if obj.coverage < 70:
                # Check if we have any evidence matching objective keywords
                obj_keywords = set(re.findall(r'\w{4,}', obj.objective.lower()))
                if not (obj_keywords & evidence_topics):
                    result.gaps.append(ResearchGap(
                        topic=obj.objective,
                        reason_missing="No direct evidence found matching objective keywords.",
                        suggested_queries=[f"{obj.objective} detailed evidence", f"{obj.objective} data statistics"],
                        estimated_confidence_improvement=15.0
                    ))

        # 3. Deterministic Confidence (Phase 4)
        confidence = calculate_production_confidence(ConfidenceInput(
            objective_states=res_states,
            summaries=summaries,
            contradictions=result.contradictions,
            evidence_count=total_evidence,
            iterations=current_iteration
        ))

        result.confidence_breakdown = confidence
        result.continue_research = result.continue_research and current_iteration < 3

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
