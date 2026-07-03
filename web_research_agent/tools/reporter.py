import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ArticleSummary, ResearchPlan, Contradiction,
    EvidenceItem, ResearchReport, ConfidenceBreakdown, ResearchGap, SelfEvaluation
)
from web_research_agent.config import OUTPUT_DIR, EXPORT_FORMATS

logger = logging.getLogger(__name__)

def generate_final_report(
    summaries: List[ArticleSummary],
    plan: ResearchPlan,
    llm_client: LLMClient,
    evidence_items: List[EvidenceItem],
    contradictions: List[Contradiction],
    confidence: ConfidenceBreakdown,
    gaps: List[ResearchGap]
) -> str:
    """
    Enhanced synthesis engine with academic citations and dashboard.
    """
    evidence_text = "\n".join([f"SOURCE [{i+1}]: {s.url}\nCONTENT: {s.summary}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic}
    OBJECTIVES: {plan.objectives}
    SOURCES & EVIDENCE:
    {evidence_text[:12000]}

    TASK: Write an analyst-grade research report.
    - Style: Formal, concise, data-driven.
    - Citations: Use inline numbers like [1], [2, 3] to attribute every major fact to the source index.

    REPORT STRUCTURE:
    # {plan.topic}

    ## Executive Dashboard
    (Top-line conclusions and a Research Scorecard)

    ## Key Takeaways
    (3-5 critical insights)

    ## Background

    ## Detailed Analysis
    (Synthesized analysis using inline citations [1], [2], etc.)

    ## Supporting Evidence
    (Structured claims and attributed sources)

    ## Contradictions & Conflicts

    ## Research Gaps
    (What remains unknown)

    ## Confidence Breakdown
    (Detailed explanation of the {confidence.overall}/100 score)

    ## References
    (Mapped to the numbers used in citations)

    ## Further Reading
    """
    sys_prompt = "Senior Analyst Synthesis Engine. Use academic citation format [n]. High professional quality only."

    try:
        report_content = llm_client.call(prompt, sys_prompt)
        return report_content
    except Exception as e:
        logger.error(f"Report synthesis failed: {e}")
        return "# Synthesis Failed\nRaw summaries provided below.\n" + evidence_text

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def export_report(content: str, plan: ResearchPlan, state_data: Dict):
    """Handles multi-format exports."""
    base_name = "report"

    if "markdown" in EXPORT_FORMATS:
        with open(OUTPUT_DIR / f"{base_name}.md", "w", encoding="utf-8") as f:
            f.write(content)

    if "json" in EXPORT_FORMATS:
        with open(OUTPUT_DIR / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, cls=DateTimeEncoder)

    if "html" in EXPORT_FORMATS:
        html_wrapper = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; }}
                h1, h2 {{ border-bottom: 1px solid #eee; }}
                pre {{ background: #f4f4f4; padding: 15px; overflow: auto; }}
            </style>
        </head>
        <body>
            {content.replace('# ', '<h1>').replace('## ', '<h2>').replace('### ', '<h3>').replace('\n', '<br>')}
        </body>
        </html>
        """
        with open(OUTPUT_DIR / f"{base_name}.html", "w", encoding="utf-8") as f:
            f.write(html_wrapper)

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
        "overall_grade": "A/B/C/D/F",
        "justification": "Short reason for grade",
        "coverage_score": 0.0,
        "evidence_score": 0.0,
        "readability_score": 0.0,
        "citation_quality": 0.0,
        "objectivity": 0.0,
        "bias_risk": 0.0,
        "novel_insights": 0.0
    }}
    """
    sys_prompt = "You are an AI Quality Auditor. Be strict and objective."

    try:
        data = llm_client.get_json(prompt, sys_prompt)
        return SelfEvaluation(**data)
    except Exception as e:
        logger.error(f"Self-evaluation failed: {e}")
        return SelfEvaluation(
            overall_grade="U", justification="Evaluation engine failed."
        )
