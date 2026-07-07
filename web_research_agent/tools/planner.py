import logging
import time
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchPlan, QueryIntent, PipelineResult
import json

logger = logging.getLogger(__name__)

def generate_research_plan(query: str, llm_client: LLMClient) -> PipelineResult[ResearchPlan]:
    """
    Detects query intent and generates a strategic research plan with multiple objectives.
    """
    start_time = time.time()
    sys_prompt = "You are a professional research planner. Analyze the query and output a structured JSON plan."

    prompt = f"""
    Analyze the user query: "{query}"

    1. Determine the intent: Biography, Technology, Programming, Finance, Medical, Cybersecurity, History, Business, or General.
    2. Generate 6-10 specific research objectives tailored to this intent.
    3. Generate 6-10 focused, high-precision search queries.
       - Avoid large OR-based boolean queries.
       - Each query should target a specific aspect of the topic.
       - Prioritize academic sources, official docs, and primary evidence.

    Return JSON:
    {{
        "topic": "Concise topic name",
        "intent": "Detected Category",
        "objectives": ["Objective 1", "Objective 2", ...],
        "queries": ["Search query 1", "Search query 2", ...]
    }}
    """

    try:
        plan = llm_client.get_json(prompt, sys_prompt, response_model=ResearchPlan)
        return PipelineResult(
            success=True,
            payload=plan,
            stage="planning",
            timing=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        # Deterministic Fallback Plan (Phase 5)
        fallback_plan = ResearchPlan(
            topic=query,
            intent=QueryIntent.GENERAL,
            objectives=[
                f"Historical context and origins of {query}",
                f"Core components and internal mechanics of {query}",
                f"Major stakeholders and influential entities in the field of {query}",
                f"Current market trends and real-world applications of {query}",
                f"Primary challenges, risks, and controversies surrounding {query}",
                f"Future outlook and emerging developments for {query}"
            ],
            queries=[
                query,
                f"history and development of {query}",
                f"technical specifications and components of {query}",
                f"top organizations and leaders in {query}",
                f"market analysis and case studies for {query}",
                f"challenges and future trends of {query}"
            ]
        )
        return PipelineResult(
            success=False,
            payload=fallback_plan,
            errors=[str(e)],
            stage="planning",
            timing=time.time() - start_time
        )
