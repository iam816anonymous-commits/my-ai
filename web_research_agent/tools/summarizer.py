import logging
import re
import time
from typing import List, Dict, Tuple, Optional
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ArticleSummary, PipelineResult
from web_research_agent.config import MAX_SUMMARY_WORDS

logger = logging.getLogger(__name__)

def summarize_article(text: str, llm_client: LLMClient, query: str = "", url: str = "") -> PipelineResult[List[Dict[str, str]]]:
    """Compatibility wrapper for individual article summarization."""
    return batch_summarize_documents([{"url": url, "text": text}], llm_client, query)

def batch_summarize_documents(documents: List[Dict[str, str]], llm_client: LLMClient, query: str = "") -> PipelineResult[List[Dict[str, str]]]:
    """
    Summarizes multiple documents in a single LLM call to save tokens and reduce latency (Phase 3).
    """
    start_time = time.time()
    if not documents:
        return PipelineResult(success=False, errors=["No documents provided"], stage="summarization")

    # Limit context size per document to ensure batch fits in window
    # Target 3-5 documents per batch
    batch_content = ""
    for i, doc in enumerate(documents, 1):
        batch_content += f"DOCUMENT {i} (URL: {doc['url']}):\n{doc['text'][:3000]}\n\n"

    sys_prompt = "Senior Research Analyst. Extract precise claims, statistics, dates, and evidence from multiple sources. Output structured JSON."
    prompt = f"""
    Research Query: {query}

    {batch_content}

    TASK:
    Analyze the documents above and extract key findings for each.
    Return a JSON object with a 'summaries' list.
    Each item must have:
    - url: The document URL
    - summary: A 150-250 word synthesis of findings, claims, and stats.
    - evidence_strength: Strong, Moderate, or Weak.

    JSON format:
    {{
      "summaries": [
        {{ "url": "...", "summary": "...", "evidence_strength": "..." }},
        ...
      ]
    }}
    """

    try:
        from web_research_agent.models.schemas import BatchSummaryResult
        data = llm_client.get_json(prompt, sys_prompt, response_model=BatchSummaryResult)

        return PipelineResult(
            success=True,
            payload=data.summaries,
            stage="summarization",
            timing=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Batch LLM Summarization failed: {e}")
        return PipelineResult(success=False, errors=[str(e)], stage="summarization", timing=time.time() - start_time)
