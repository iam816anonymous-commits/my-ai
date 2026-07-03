import logging
import json
import re
from typing import List, Dict, Optional
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
    """Analytical synthesis with academic citations."""
    evidence_text = "\n".join([f"SOURCE [{i+1}]: {s.url} ({s.source_type})\n{s.summary}" for i, s in enumerate(summaries)])

    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent}
    SOURCES & EVIDENCE: {evidence_text[:12000]}

    TASK: Analytical synthesis (McKinsey/Gartner style).
    - Use inline academic citations: [1], [2, 4].
    - Cross-reference sources. Explain conflicts.

    STRUCTURE:
    # {plan.topic}
    ## Executive Dashboard (Conclusion + Scorecard)
    ## Key Takeaways
    ## Background
    ## Detailed Analysis (Synthesized, cited [1])
    ## Supporting Evidence (Claims, Sources, Strength)
    ## Contradictions & Conflicts
    ## Research Gaps (Detailed analysis)
    ## Confidence Breakdown ({confidence.overall}/100)
    ## References (Numbered 1, 2...)
    ## Further Reading
    """
    try:
        content = llm_client.call(prompt, "Senior Analyst Synthesis Engine. Use citations.")
        return validate_and_repair_report(content, summaries)
    except Exception as e:
        logger.error(f"Synthesis fail: {e}")
        return "# Synthesis Failed\n" + evidence_text

def validate_and_repair_report(content: str, summaries: List[ArticleSummary]) -> str:
    """Repairs malformed citations and removes duplicates."""
    # Simple deduplication of sections if any
    lines = content.split('\n')
    seen_headers = set()
    cleaned_lines = []
    for line in lines:
        if line.startswith('## '):
            if line in seen_headers: continue
            seen_headers.add(line)
        cleaned_lines.append(line)

    repaired = '\n'.join(cleaned_lines)
    # Ensure references are present
    if "## References" not in repaired:
        ref_list = "\n".join([f"[{i+1}] {s.url}" for i, s in enumerate(summaries)])
        repaired += f"\n\n## References\n{ref_list}"
    return repaired

def export_report(content: str, plan: ResearchPlan, state_data: Dict):
    base = "report"
    if "markdown" in EXPORT_FORMATS:
        with open(OUTPUT_DIR / f"{base}.md", "w") as f: f.write(content)
    if "json" in EXPORT_FORMATS:
        from web_research_agent.tools.reporter import DateTimeEncoder
        with open(OUTPUT_DIR / f"{base}.json", "w") as f: json.dump(state_data, f, indent=2, cls=DateTimeEncoder)
    if "html" in EXPORT_FORMATS:
        html = f"<html><body>{content.replace('# ', '<h1>').replace('## ', '<h2>').replace('\\n', '<br>')}</body></html>"
        with open(OUTPUT_DIR / f"{base}.html", "w") as f: f.write(html)

def run_self_evaluation(report: str, plan: ResearchPlan, llm_client: LLMClient) -> SelfEvaluation:
    prompt = f"Topic: {plan.topic}\nReport: {report[:8000]}\nEvaluate quality (A-F). JSON: overall_grade, justification, coverage_score, evidence_score, readability_score."
    try:
        return SelfEvaluation(**llm_client.get_json(prompt, "AI Auditor."))
    except:
        return SelfEvaluation(overall_grade="U", justification="Evaluation failed.")

from datetime import datetime
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime): return obj.isoformat()
        return super().default(obj)
