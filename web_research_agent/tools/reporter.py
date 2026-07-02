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

    summary_text = "\n\n".join([f"### Source: {s.url}\n{s.summary}" for s in summaries])
    references = "\n".join([f"- {s.url}" for s in summaries])

    prompt = f"""
    Write a research report for "{plan.topic}".
    Objectives: {', '.join(plan.objectives)}
    Iterations: {iterations}
    Summaries: {summary_text[:8000]} # Limit to save tokens
    """
    sys_prompt = "Professional report. Markdown. Focus on synthesis."

    try:
        report = llm_client.call(prompt, sys_prompt)
        return report
    except Exception as e:
        logger.warning(f"LLM Report generation failed: {e}. Using no-LLM fallback.")
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
        "## Research Objectives",
        "\n".join([f"- {obj} ({coverage.get(obj, 0)}% coverage)" for obj in plan.objectives]),
        "## Methodology",
        f"Research performed over {iterations} iterations using automated web search and extraction.",
        "## Article Summaries"
    ]

    for s in summaries:
        sections.append(f"### {s.url}\n{s.summary}")

    if contradictions:
        sections.append("## Contradictions Detected")
        for c in contradictions:
            sections.append(f"- **Conflict**: {c.claim_a} VS {c.claim_b}\n  **Sources**: {c.source_a} AND {c.source_b}")

    sections.append("## References")
    sections.append("\n".join([f"- {s.url}" for s in summaries]))

    sections.append("## Limitations")
    sections.append("This is a fallback report generated without LLM synthesis due to API unavailability.")

    return "\n\n".join(sections)
