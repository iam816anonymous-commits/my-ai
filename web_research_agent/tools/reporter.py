import logging
from typing import List, Dict, Optional
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ArticleSummary, ResearchPlan, Contradiction,
    EvidenceItem, SelfEvaluation, ResearchReport
)

logger = logging.getLogger(__name__)

def generate_final_report(
    summaries: List[ArticleSummary],
    plan: ResearchPlan,
    llm_client: LLMClient,
    evidence_items: List[EvidenceItem],
    contradictions: List[Contradiction],
    confidence_score: float
) -> str:
    """
    Synthesis engine that produces a Gartner/McKinsey style analytical report.
    """
    evidence_text = "\n".join([f"- {s.url}: {s.summary}" for s in summaries])

    prompt = f"""
    TOPIC: {plan.topic}
    INTENT: {plan.intent}
    OBJECTIVES: {plan.objectives}
    RAW EVIDENCE:
    {evidence_text[:12000]}

    TASK: Synthesize a professional research report.
    - Style: Analytical, formal, concise (McKinsey/Gartner style).
    - Synthesis: Cross-reference sources. DO NOT just list summaries.
    - Connections: Contrast different viewpoints and highlight agreements.

    REPORT STRUCTURE:
    # Executive Summary (Bottom-line findings)
    # Key Findings (Bullet points of core facts)
    # Background (Context and history)
    # Detailed Analysis (Synthesis of technical/thematic details)
    # Supporting Evidence (Structured claims and sources)
    # Contradictions (Conflicts and explanations)
    # Limitations (Gaps in research)
    # Confidence Assessment (Why the score is {confidence_score}/100)
    # References

    Confidence Score: {confidence_score}/100
    """
    sys_prompt = "You are a senior research analyst. Output a high-fidelity, evidence-driven Markdown report."

    try:
        return llm_client.call(prompt, sys_prompt)
    except Exception as e:
        logger.error(f"Report synthesis failed: {e}")
        return "# Report Generation Failed\n\nPlease check logs for details."

def run_self_evaluation(report_content: str, plan: ResearchPlan, llm_client: LLMClient) -> SelfEvaluation:
    """
    Automatically evaluates the quality of the generated report.
    """
    prompt = f"""
    Analyze the following research report for quality and objectivity.
    TOPIC: {plan.topic}
    REPORT:
    {report_content[:8000]}

    Return JSON evaluation:
    {{
        "coverage_score": 0-100,
        "evidence_score": 0-100,
        "readability_score": 0-100,
        "citation_quality": 0-100,
        "objectivity": 0-100,
        "bias_risk": 0-100,
        "novel_insights": 0-100,
        "overall_grade": "A/B/C/D/F",
        "justification": "Short reason for grade"
    }}
    """
    sys_prompt = "You are an AI Quality Auditor. Be strict and objective."

    try:
        data = llm_client.get_json(prompt, sys_prompt)
        return SelfEvaluation(**data)
    except Exception as e:
        logger.error(f"Self-evaluation failed: {e}")
        return SelfEvaluation(
            coverage_score=0, evidence_score=0, readability_score=0,
            citation_quality=0, objectivity=0, bias_risk=0, novel_insights=0,
            overall_grade="U", justification="Evaluation engine failed."
        )
