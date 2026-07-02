from typing import List, Dict
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import ArticleSummary, ResearchPlan, Contradiction
import logging

logger = logging.getLogger(__name__)

def generate_final_report(
    summaries: List[ArticleSummary],
    plan: ResearchPlan,
    llm_client: LLMClient,
    iterations: int = 1,
    coverage: Dict[str, float] = None,
    contradictions: List[Contradiction] = None
) -> str:
    """
    Assembles the final report. Includes LLM synthesis with a robust non-LLM fallback.
    """
    coverage = coverage or {}
    contradictions = contradictions or []

    # Compress summaries for reporting to save tokens
    summary_text = "\n\n".join([f"Source: {s.url}\nSummary: {s.summary[:500]}" for s in summaries])

    prompt = f"""
    Topic: {plan.topic}
    Objectives: {plan.objectives}
    Iterations: {iterations}
    Coverage: {coverage}
    Summaries: {summary_text[:6000]}

    Write a comprehensive MD report. Include:
    # {plan.topic}
    ## Executive Summary
    ## Research Objectives
    ## Methodology
    ## Source Summaries
    ## Final Conclusion
    ## Coverage Matrix
    ## Contradictions
    ## Evidence Summary
    ## References
    """
    sys_prompt = "Professional researcher. MD format. Concise."

    try:
        return llm_client.call(prompt, sys_prompt)
    except Exception as e:
        logger.warning(f"LLM Report synthesis failed: {e}. Generating non-LLM report.")
        return generate_no_llm_fallback_report(plan, summaries, iterations, coverage, contradictions)

def generate_no_llm_fallback_report(
    plan: ResearchPlan,
    summaries: List[ArticleSummary],
    iterations: int,
    coverage: Dict[str, float],
    contradictions: List[Contradiction]
) -> str:
    """Generates report.md without LLM."""
    sections = [
        f"# Research Report: {plan.topic}",
        "## Executive Summary",
        "This report was generated using a fallback mechanism. Automated synthesis was unavailable.",
        "## Research Objectives",
        "\n".join([f"- {obj}" for obj in plan.objectives]),
        "## Methodology",
        f"Automated iterative research ({iterations} cycles). Top {len(summaries)} sources processed.",
        "## Article Summaries"
    ]

    for s in summaries:
        sections.append(f"### {s.url}\n{s.summary}")

    sections.append("## Coverage Matrix")
    sections.append("\n".join([f"- {obj}: {coverage.get(obj, 0.0)}%" for obj in plan.objectives]))

    if contradictions:
        sections.append("## Contradictions")
        for c in contradictions:
            sections.append(f"- **Conflict**: {c.claim_a} vs {c.claim_b}\n  Sources: {c.source_a}, {c.source_b}")

    sections.append("## Evidence Summary")
    sections.append(f"Collected {len(summaries)} articles covering the research objectives.")

    sections.append("## References")
    sections.append("\n".join([f"- {s.url}" for s in summaries]))

    sections.append("## Limitations")
    sections.append("Synthesis unavailable. Direct summaries provided.")

    return "\n\n".join(sections)
