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
    contradictions: List[Contradiction] = None,
    confidence_score: float = 0.0
) -> str:
    """
    Generates a professional research report by synthesizing multiple sources.
    """
    coverage = coverage or {}
    contradictions = contradictions or []

    # Condense summaries for synthesis
    condensed_summaries = ""
    for i, s in enumerate(summaries, 1):
        condensed_summaries += f"SOURCE {i} ({s.url}):\n{s.summary}\n\n"

    prompt = f"""
    Topic: {plan.topic}
    Research Objectives: {plan.objectives}
    Collected Evidence:
    {condensed_summaries[:8000]}

    Task: Write a professional research report.
    - DO NOT just list summaries.
    - Synthesize information across sources for each section.
    - Use a formal, analytical tone.
    - Identify areas of agreement and disagreement.
    - Ensure clear structure.

    Required Structure:
    # {plan.topic}
    ## Executive Summary
    ## Key Findings
    ## Background
    ## Detailed Analysis
    ## Supporting Evidence
    ## Contradictions
    ## Limitations
    ## Confidence Assessment
    ## References

    Confidence Score: {confidence_score}/100
    Coverage Data: {coverage}
    """
    sys_prompt = "You are a senior research analyst. Write a high-quality, synthesized report. Avoid repetition. Do not mention 'Source A says'. Write naturally."

    try:
        report = llm_client.call(prompt, sys_prompt)
        # Ensure references are present
        if "## References" not in report:
            report += "\n\n## References\n" + "\n".join([f"- {s.url}" for s in summaries])
        return report
    except Exception as e:
        logger.warning(f"LLM Report synthesis failed: {e}. Generating fallback report.")
        from web_research_agent.tools.reporter import generate_no_llm_fallback_report
        return generate_no_llm_fallback_report(plan, summaries, iterations, coverage, contradictions, confidence_score)

def generate_no_llm_fallback_report(
    plan: ResearchPlan,
    summaries: List[ArticleSummary],
    iterations: int,
    coverage: Dict[str, float],
    contradictions: List[Contradiction],
    confidence_score: float
) -> str:
    """Generates a structured report.md without LLM."""
    sections = [
        f"# Research Report: {plan.topic}",
        "## Executive Summary",
        "This report is an automated synthesis of collected research data. Detailed analysis is provided below.",
        "## Key Findings",
        "Findings are based on the following sources. See 'Supporting Evidence' for details.",
        "## Research Objectives",
        "\n".join([f"- {obj}: {coverage.get(obj, 0.0)}% coverage" for obj in plan.objectives]),
        "## Methodology",
        f"Professional iterative research process completed over {iterations} cycles.",
        "## Supporting Evidence"
    ]

    for s in summaries:
        sections.append(f"### Evidence from {s.url}\n{s.summary}")

    sections.append("## Contradictions")
    if contradictions:
        for c in contradictions:
            sections.append(f"- **Conflict**: {c.claim_a} vs {c.claim_b}\n  Sources: {c.source_a}, {c.source_b}")
    else:
        sections.append("No significant contradictions were detected during the research process.")

    sections.append("## Confidence Assessment")
    sections.append(f"Final Research Confidence: {confidence_score}/100. This score reflects objective coverage and source reliability.")

    sections.append("## References")
    sections.append("\n".join([f"- {s.url}" for s in summaries]))

    return "\n\n".join(sections)
