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
    """
    summaries_joined = "\n---\n".join([f"Source: {s.url}\nSummary: {s.summary}" for s in summaries])

    prompt = f"""
    Topic: {plan.topic}
    Objectives: {plan.objectives}
    Knowledge: {summaries_joined[:10000]}

    Evaluate coverage. Return JSON:
    - completed_objectives: [list]
    - missing_objectives: [list]
    - contradictions: [{{claim_a, claim_b, source_a, source_b, explanation}}]
    - confidence: 0-100
    - objective_coverage: {{objective: %}}
    - follow_up_queries: [list of 3 queries]
    - continue_research: bool
    """
    sys_prompt = "Reasoning agent. JSON only. Be critical."

    try:
        data = llm_client.get_json(prompt, sys_prompt)
        # Basic validation of expected fields
        required = ["completed_objectives", "missing_objectives", "objective_coverage", "continue_research"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing field in reasoning: {field}")

        return ReasoningResult(**data)
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        # Default to stop if reasoning fails to avoid infinite loops or extra costs
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
        # Simple heuristic: if summary mentions objective, it's covered
        covered = [obj for obj in plan.objectives if any(word.lower() in s.summary.lower() for word in obj.split())]

        kb.append(KnowledgeBaseEntry(
            summary=s.summary,
            source=s.url,
            confidence=0.8, # Default
            covered_objectives=covered,
            supporting_evidence=s.summary[:200]
        ))
    return kb
