import logging
import json
import re
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
    summaries: List[ArticleSummary], plan: ResearchPlan, llm_client: LLMClient,
    evidence_items: List[EvidenceItem], contradictions: List[Contradiction],
    confidence: ConfidenceBreakdown, gaps: List[ResearchGap]
) -> str:
    """Synthesizes analyst-grade report with citations and recommendations."""
    evidence_text = "\n".join([f"SOURCE [{i+1}]: {s.url} ({s.source_type}, Tier {s.source_tier})\n{s.summary}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent}
    SOURCES: {evidence_text[:15000]}

    TASK: Synthesize a professional analyst report.
    - Inline Citations: [1], [2, 5].
    - Focus: Comparison, causality, tradeoffs, and strategic implications.
    - Style: Gartner/McKinsey. Analytical and concise.

    STRUCTURE:
    # {plan.topic}
    ## Executive Dashboard (Conclusion + Scorecard)
    ## Executive Recommendations (Strategic advice for leadership)
    ## Practical Applications (Real-world use cases)
    ## Decision Maker Notes (One-paragraph summary)
    ## Detailed Analysis (Synthesized themes with citations [n])
    ## Supporting Evidence (Claims, Sources, Strength Justification)
    ## Contradictions & Conflicts
    ## Research Gaps (Detailed analysis)
    ## Confidence Breakdown ({confidence.overall}/100)
    ## References (Numbered list)
    ## Further Reading
    """
    try:
        content = llm_client.call(prompt, "Senior Analyst Platform. No generic AI fluff.")
        return validate_and_repair_report(content, summaries)
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return "# Report Generation Failed\n\nRaw evidence attached in JSON."

def validate_and_repair_report(content: str, summaries: List[ArticleSummary]) -> str:
    """Removes duplication and malformed markers."""
    lines = content.split('\n')
    seen_headers = set()
    cleaned = []
    for l in lines:
        if l.startswith('## '):
            if l in seen_headers: continue
            seen_headers.add(l)
        cleaned.append(l)

    repaired = '\n'.join(cleaned)
    if "## References" not in repaired:
        ref_text = "\n\n## References\n" + "\n".join([f"[{i+1}] {s.url}" for i, s in enumerate(summaries)])
        repaired += ref_text
    return repaired

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime): return obj.isoformat()
        return super().default(obj)

def export_report(content: str, plan: ResearchPlan, state_data: Dict, storage):
    """Exports multi-format results via StorageManager."""
    rid = state_data.get("report_id", "latest")

    # Save primary markdown
    storage.save_artifact(rid, "report", content, "md")

    # Save exports
    if "json" in EXPORT_FORMATS:
        storage.save_artifact(rid, "json", state_data, "json")

    if "html" in EXPORT_FORMATS:
        html = f"<html><body>{content.replace('# ', '<h1>').replace('## ', '<h2>').replace('\\n', '<br>')}</body></html>"
        storage.save_artifact(rid, "html", html, "html")

def run_self_evaluation(report: str, plan: ResearchPlan, llm_client: LLMClient) -> SelfEvaluation:
    prompt = f"Topic: {plan.topic}\nReport: {report[:8000]}\nJSON evaluation: overall_grade, justification, coverage_score, evidence_score."
    try:
        return SelfEvaluation(**llm_client.get_json(prompt, "AI Quality Auditor."))
    except:
        return SelfEvaluation(overall_grade="U", justification="Audit failed.")
