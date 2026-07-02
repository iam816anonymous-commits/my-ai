from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ResearchPlan
from tenacity import retry, stop_after_attempt, wait_exponential
import json
import logging

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_research_plan(query: str, llm_client: LLMClient) -> ResearchPlan:
    """
    Generates a research plan with objectives and search queries based on the user query.
    Retries up to 3 times on failure.
    """
    prompt = f"""
    You are a professional research planner. Analyze the following user query and create a structured research plan.

    User Query: "{query}"

    Return a JSON object with the following fields:
    - topic: A concise name for the research topic.
    - objectives: A list of 5-10 key research objectives.
    - queries: A list of 5-10 diverse and specific search queries to cover all aspects of the topic.

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
        if not content:
             raise ValueError("LLM returned empty content for research plan.")

        plan_data = json.loads(content)

        # Validation
        if "topic" not in plan_data or "objectives" not in plan_data or "queries" not in plan_data:
            raise ValueError(f"Missing required fields in research plan: {plan_data.keys()}")

        if not (5 <= len(plan_data["queries"]) <= 10):
            logger.warning(f"Planner generated {len(plan_data['queries'])} queries, which is outside the preferred 5-10 range.")

        return ResearchPlan(**plan_data)
    except Exception as e:
        logger.error(f"Attempt failed to generate research plan: {str(e)}")
        raise e # Let tenacity handle retries

def get_fallback_plan(query: str) -> ResearchPlan:
    """
    Provides a basic fallback plan if the intelligent planner fails after retries.
    """
    return ResearchPlan(
        topic=query,
        objectives=[f"Research the core aspects of {query}"],
        queries=[query, f"{query} overview", f"{query} details", f"{query} latest trends", f"{query} examples"]
    )
