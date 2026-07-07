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
        data = llm_client.get_json(prompt, sys_prompt)

        # Ensure intent is a valid QueryIntent
        intent_str = data.get("intent", "General").upper()
        try:
            intent = QueryIntent[intent_str]
        except KeyError:
            # Fallback for common mismatches
            if "TECH" in intent_str: intent = QueryIntent.TECHNOLOGY
            elif "SECURITY" in intent_str: intent = QueryIntent.CYBERSECURITY
            else: intent = QueryIntent.GENERAL

        data["intent"] = intent
        plan = ResearchPlan(**data)
        return PipelineResult(
            success=True,
            payload=plan,
            stage="planning",
            timing=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        fallback_plan = ResearchPlan(
            topic=query,
            intent=QueryIntent.GENERAL,
            objectives=[f"General overview of {query}", "Key stakeholders", "Current status", "Challenges", "Future outlook"],
            queries=[query, f"{query} details", f"{query} analysis", f"{query} research"]
        )
        return PipelineResult(
            success=False,
            payload=fallback_plan,
            errors=[str(e)],
            stage="planning",
            timing=time.time() - start_time
        )
