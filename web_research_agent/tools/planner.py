from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchPlan
import json
import logging

logger = logging.getLogger(__name__)

def generate_research_plan(query: str, llm_client: LLMClient) -> ResearchPlan:
    """
    Generates a research plan with objectives and search queries based on the user query.
    """
    prompt = f"""
    You are a professional research planner. Analyze the following user query and create a structured research plan.

    User Query: "{query}"

    Return a JSON object with the following fields:
    - topic: A concise name for the research topic.
    - objectives: A list of at least 5 key research objectives.
    - queries: A list of at least 6 diverse search queries to cover all aspects of the topic.

    Example output format:
    {{
        "topic": "Agentic AI",
        "objectives": ["Define Agentic AI", "Explain architecture", ...],
        "queries": ["Agentic AI definition", "Agentic AI architecture", ...]
    }}

    Ensure the response is ONLY the JSON object.
    """
    try:
        response = llm_client.client.chat.completions.create(
            model=llm_client.model,
            messages=[
                {"role": "system", "content": "You are a professional research planner. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.2
        )
        content = response.choices[0].message.content
        plan_data = json.loads(content)
        return ResearchPlan(**plan_data)
    except Exception as e:
        logger.error(f"Failed to generate research plan: {e}")
        # Fallback plan
        return ResearchPlan(
            topic=query,
            objectives=[f"Research {query}"],
            queries=[query]
        )
