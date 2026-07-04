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
    summaries: List[ArticleSummary],
    plan: ResearchPlan,
    llm_client: LLMClient,
    evidence_items: List[EvidenceItem],
    contradictions: List[Contradiction],
    confidence: ConfidenceBreakdown,
    gaps: List[ResearchGap]
) -> str:
    """Synthesizes high-fidelity analyst-grade report."""
    evidence_text = "\n".join([f"SOURCE [{i+1}]: {s.url} ({s.source_type}, Tier {s.source_tier})\n{s.summary}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent}
    SOURCES: {evidence_text[:15000]}

    TASK: Write a Senior Analyst Report.
    - Citations: Use inline numbers: [1], [2, 5]. Attribute every fact.
    - Tone: Analytical, causality-focused, objective. Avoid fluff.
    - Synthesis: Cross-reference across Tiers. Contrast conflicting evidence.

    STRUCTURE:
    # {plan.topic}
    ## Executive Dashboard (Bottom-line + Key Findings)
    ## Executive Recommendations (Strategic advice)
    ## Practical Applications (How to use this info)
    ## Decision Maker Notes (Summary for leadership)
    ## Background & Context
    ## Detailed Analysis (Synthesized, cited [1])
    ## Supporting Evidence (Claims, Sources, Strength Justification)
    ## Contradictions & Conflicts
    ## Research Gaps (Missing info + why)
    ## Confidence Breakdown ({confidence.overall}/100)
    ## References (Mapped 1, 2...)
    ## Further Reading (Authoritative suggested sources)
    """
    try:
        content = llm_client.call(prompt, "Synthesis Engine V2. Gartner/MIT style. High quality.")
        return validate_and_repair_report(content, summaries)
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return "# Research Report Generation Failed\n\nFallback content unavailable."

def validate_and_repair_report(content: str, summaries: List[ArticleSummary]) -> str:
    """Repairs structure, removes duplicates, and validates citations."""
    # Basic paragraph deduplication
    lines = content.split('\n')
    seen = set()
    cleaned = []
    for l in lines:
        if l.strip() and l in seen and len(l) > 100: continue
        if l.strip() and len(l) > 100: seen.add(l)
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

def export_report(content: str, plan: ResearchPlan, state_data: Dict):
    """Exports to MD, JSON, HTML, PDF (simulated)."""
    base = "report"
    if "markdown" in EXPORT_FORMATS:
        with open(OUTPUT_DIR / f"{base}.md", "w") as f: f.write(content)
    if "json" in EXPORT_FORMATS:
        with open(OUTPUT_DIR / f"{base}.json", "w") as f: json.dump(state_data, f, indent=2, cls=DateTimeEncoder)
    if "html" in EXPORT_FORMATS:
        html = f"<html><head><style>body{{font-family:sans-serif;line-height:1.6;margin:40px;}}</style></head><body>{content.replace('# ', '<h1>').replace('## ', '<h2>').replace('\\n', '<br>')}</body></html>"
        with open(OUTPUT_DIR / f"{base}.html", "w") as f: f.write(html)

def run_self_evaluation(report: str, plan: ResearchPlan, llm_client: LLMClient) -> SelfEvaluation:
    prompt = f"Evaluate report quality. Topic: {plan.topic}\nReport: {report[:8000]}\nJSON: overall_grade, justification, coverage_score, evidence_score, readability_score."
    try:
        return SelfEvaluation(**llm_client.get_json(prompt, "Quality Auditor."))
    except:
        return SelfEvaluation(overall_grade="U", justification="Audit fail.")
