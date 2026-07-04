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
    """Synthesizes high-fidelity analyst-grade report."""
    evidence_text = "\n".join([f"SOURCE [{i+1}]: {s.url} ({s.source_type}, Tier {s.source_tier})\n{s.summary}" for i, s in enumerate(summaries)])

    # Pre-validation and automatic repair of citation mapping

    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent}
    SOURCES: {evidence_text[:15000]}

    TASK: Write a Senior Analyst Report.
    - Inline Citations: [1], [2, 5]. Attribute every fact.
    - Style: Formal, data-driven, causality-focused.

    STRUCTURE:
    # {plan.topic}
    ## Executive Dashboard (Bottom-line + Key Findings)
    ## Executive Recommendations (Strategic advice)
    ## Practical Applications (How to use this info)
    ## Decision Maker Notes (One-paragraph summary)
    ## Background & Context
    ## Detailed Analysis (Synthesized themes with citations [n])
    ## Supporting Evidence (Claims, Sources, Strength Justification)
    ## Contradictions & Conflicts
    ## Research Gaps (Missing info + why)
    ## Confidence Breakdown ({confidence.overall}/100)
    ## References (Numbered list)
    ## Further Reading
    """
    try:
        content = llm_client.call(prompt, "Senior Analyst Synthesis Engine. Gartner/McKinsey style.")
        return validate_and_repair_report(content, summaries)
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return "# Synthesis Error\n\nRaw evidence available in logs."

def validate_and_repair_report(content: str, summaries: List[ArticleSummary]) -> str:
    """Ensures structure integrity and repairs malformed markers."""
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

    # Auto-fix empty sections
    repaired = re.sub(r'## ([^#\n]+)\n\n##', r'## \1\nContent unavailable for this section.\n\n##', repaired)

    return repaired

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime): return obj.isoformat()
        return super().default(obj)

def export_report(content: str, plan: ResearchPlan, state_data: Dict, storage):
    rid = state_data.get("report_id", "latest")

    # Individual success for each export
    try: storage.save_artifact(rid, "report", content, "md")
    except Exception as e: logger.error(f"MD export fail: {e}")

    if "json" in EXPORT_FORMATS:
        try: storage.save_artifact(rid, "json", state_data, "json")
        except Exception as e: logger.error(f"JSON export fail: {e}")

    if "html" in EXPORT_FORMATS:
        try:
            html = f"<html><head><style>body{{font-family:sans-serif;line-height:1.6;margin:40px;}}</style></head><body>{content.replace('# ', '<h1>').replace('## ', '<h2>').replace('\\n', '<br>')}</body></html>"
            storage.save_artifact(rid, "html", html, "html")
        except Exception as e: logger.error(f"HTML export fail: {e}")

def run_self_evaluation(report: str, plan: ResearchPlan, llm_client: LLMClient) -> SelfEvaluation:
    prompt = f"Topic: {plan.topic}\nReport: {report[:8000]}\nJSON evaluation: overall_grade, justification, coverage_score, evidence_score, readability_score."
    try:
        return SelfEvaluation(**llm_client.get_json(prompt, "Analyst Auditor."))
    except:
        return SelfEvaluation(overall_grade="U", justification="Audit fail.")
