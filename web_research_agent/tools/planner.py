import logging
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchPlan
import json

logger = logging.getLogger(__name__)

def generate_research_plan(query: str, llm_client: LLMClient) -> ResearchPlan:
    """Generates a research plan."""
    sys_prompt = "Short JSON only."
    prompt = f"Plan research for: {query}. JSON: topic, objectives (5-7), queries (5-7)."

    try:
        data = llm_client.get_json(prompt, sys_prompt)
        # Ensure it meets basic requirements
        if 'topic' not in data: data['topic'] = query
        if 'objectives' not in data: data['objectives'] = [f"Research {query}"]
        if 'queries' not in data: data['queries'] = [query]
        return ResearchPlan(**data)
    except Exception as e:
        logger.error(f"Failed to generate plan: {e}")
        return ResearchPlan(topic=query, objectives=[f"Research {query}"], queries=[query])
