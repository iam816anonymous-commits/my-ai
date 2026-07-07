import logging
import re
import time
from typing import List, Dict, Tuple, Optional
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ArticleSummary, PipelineResult
from web_research_agent.config import MAX_SUMMARY_WORDS

logger = logging.getLogger(__name__)

def summarize_article(text: str, llm_client: LLMClient, query: str = "", url: str = "") -> PipelineResult[str]:
    """
    Summarizes article while explicitly extracting evidence (Claims, Stats, Entities).
    """
    start_time = time.time()
    if not text:
        return PipelineResult(success=False, errors=["Empty text provided"], stage="summarization")

    sys_prompt = "Senior Research Analyst. Extract precise claims, statistics, dates, and evidence. Format as Markdown."
    prompt = f"""
    Research Query: {query}
    URL: {url}
    Content: {text[:4000]}

    TASK:
    1. Extract key claims and statistics with supporting context.
    2. Identify core findings, numbers, and limitations.
    3. Summarize the main topic in 150-250 words.

    If no meaningful research evidence exists, return 'NO_EVIDENCE_FOUND'.
    """

    try:
        content = llm_client.call(prompt, sys_prompt)
        if "NO_EVIDENCE_FOUND" in content or len(content) < 100:
             return PipelineResult(success=False, errors=["No meaningful research evidence found in article"], stage="summarization", timing=time.time() - start_time)

        return PipelineResult(
            success=True,
            payload=content,
            stage="summarization",
            timing=time.time() - start_time
        )
    except Exception as e:
        logger.warning(f"LLM Summarization failed: {e}")
        return PipelineResult(success=False, errors=[str(e)], stage="summarization", timing=time.time() - start_time)
