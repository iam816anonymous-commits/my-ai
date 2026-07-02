import logging
from typing import List, Dict
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ReasoningResult, ArticleSummary, ResearchPlan, KnowledgeBaseEntry
import json

logger = logging.getLogger(__name__)

def evaluate_research(
    query: str,
    plan: ResearchPlan,
    summaries: List[ArticleSummary],
    llm_client: LLMClient
) -> ReasoningResult:
    """
    Analyzes collected summaries to determine if more research is needed.
    Optimized for short prompts and robust parsing.
    """
    # Create a very condensed view of the knowledge for the LLM
    knowledge_snapshot = "\n".join([f"- {s.url}: {s.summary[:200]}..." for s in summaries])

    prompt = f"""
    Topic: {plan.topic}
    Objectives: {plan.objectives}
    Knowledge Snapshot: {knowledge_snapshot[:5000]}

    Task: Evaluate coverage. Return JSON:
    {{
        "completed_objectives": [],
        "missing_objectives": [],
        "contradictions": [{{ "claim_a": "", "claim_b": "", "source_a": "", "source_b": "", "explanation": "" }}],
        "confidence": 0-100,
        "objective_coverage": {{ "objective": 0.0 }},
        "follow_up_queries": [],
        "continue_research": bool
    }}
    """
    sys_prompt = "Critical reasoning agent. JSON only."

    try:
        data = llm_client.get_json(prompt, sys_prompt)

        # Ensure objective_coverage has all objectives
        coverage = data.get("objective_coverage", {})
        for obj in plan.objectives:
            if obj not in coverage:
                coverage[obj] = 0.0
        data["objective_coverage"] = coverage

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning evaluation failed: {e}")
        # Default stop condition on persistent failure
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
    """Adds new summaries to knowledge base (in-memory)."""
    for s in new_summaries:
        # Heuristic: match keywords from objectives
        covered = []
        summary_lower = s.summary.lower()
        for obj in plan.objectives:
            keywords = [w.lower() for w in obj.split() if len(w) > 3]
            if any(k in summary_lower for k in keywords):
                covered.append(obj)

        kb.append(KnowledgeBaseEntry(
            summary=s.summary,
            source=s.url,
            confidence=0.8,
            covered_objectives=covered,
            supporting_evidence=s.summary[:150]
        ))
    return kb
