import logging
from web_research_agent.models.llm import LLMClient
import json

logger = logging.getLogger(__name__)

def summarize_article(text: str, llm_client: LLMClient) -> str:
    """Summarizes text (max 4000 chars) to 150-250 words."""
    sys_prompt = "Summarize. 150-250 words. MD."
    # Truncate to save tokens
    truncated_text = text[:4000]
    prompt = f"Summarize: {truncated_text}\n\nInclude Topic, Findings, Numbers, Key Insights, Limitations."

    try:
        return llm_client.call(prompt, sys_prompt)
    except Exception as e:
        logger.warning(f"Summarization failed: {e}. Using fallback.")
        return generate_fallback_summary(text)

def generate_fallback_summary(text: str) -> str:
    """Simple extractive fallback summary."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return "Fallback summary (LLM unavailable): No content found."

    first = paragraphs[0]
    last = paragraphs[-1]

    # Find longest middle paragraph as 'most informative' proxy
    middle = ""
    if len(paragraphs) > 2:
        middle_paras = paragraphs[1:-1]
        middle = max(middle_paras, key=len)

    summary = f"**Fallback summary (LLM unavailable)**\n\n{first}\n\n{middle}\n\n{last}"
    return summary
