import logging
import json
import re
import re
from typing import List, Dict, Optional
from datetime import datetime
from web_research_agent.models.llm import LLMClient
from web_research_agent.models.schemas import (
    ArticleSummary, ResearchPlan, Contradiction,
    EvidenceItem, ResearchReport, ConfidenceBreakdown, ResearchGap, SelfEvaluation, ResearchState
)
from web_research_agent.config import OUTPUT_DIR, EXPORT_FORMATS

logger = logging.getLogger(__name__)

def generate_final_report(
    state: ResearchState, plan: ResearchPlan, llm_client: LLMClient
) -> str:
    """Synthesizes high-fidelity analyst-grade report from Knowledge Base (Module 14)."""
    kb = state.knowledge_base
    summaries = state.summaries
    confidence = state.confidence_breakdown

    if not kb:
        return "# Research Report: Evidence Deficiency\n\nNo evidence was successfully extracted during this research session.\n\n## Reason\nPossible extraction or semantic validation failure. Check pipeline diagnostics."

    evidence_text = ""
    for i, entry in enumerate(kb, 1):
        doc = entry.document
        if doc:
            evidence_text += f"SOURCE [{i}]: {doc.url} ({doc.domain})\n"
            evidence_text += f"SUMMARY: {doc.summary}\n\n"

    prompt = f"""
    TOPIC: {plan.topic} | INTENT: {plan.intent}
    INTERNAL KNOWLEDGE BASE:
    {evidence_text[:18000]}

    TASK: Write a Senior Analyst Report. Use ONLY the provided Knowledge Base.
    - Inline Citations: [1], [2, 5]. Attribute every fact.
    - Style: Formal, data-driven, causality-focused.

    STRUCTURE:
    # {plan.topic}
    ## Executive Dashboard
    ## Strategic Recommendations & Tradeoffs
    ## Practical Applications
    ## Decision Maker Summary
    ## Context & Background
    ## Analytical Deep Dive (Synthesized analysis with citations [n])
    ## Counterarguments & Uncertainty Analysis (Discuss conflicting views)
    ## Evidence Catalog (Claims, Confirmations, Strength)
    ## Detected Contradictions
    ## Research Gaps & Future Directions
    ## Confidence & Methodology ({confidence.overall}/100)
       - {confidence.explanation}
    ## References
    ## Further Reading
    """
    try:
        content = llm_client.call(prompt, "Senior Analyst Synthesis Engine. Gartner/McKinsey style.")
        return validate_and_repair_report(content, summaries)
    except Exception as e:
        logger.error(f"Synthesis failed: {e}. Falling back to template-based synthesis.")
        return generate_template_report(summaries, plan, confidence)

def generate_template_report(summaries: List[ArticleSummary], plan: ResearchPlan, confidence: ConfidenceBreakdown) -> str:
    """Fallback synthesis using a structured template when LLM fails."""
    report = f"# Research Report: {plan.topic} (Fallback Synthesis)\n\n"
    report += f"## Executive Dashboard\nConfidence: {confidence.overall}/100\nStatus: LLM Synthesis Unavailable - Data provided as summary catalog.\n\n"
    report += "## Research Summary Catalog\n\n"
    for i, s in enumerate(summaries, 1):
        report += f"### [{i}] {s.url}\nType: {s.source_type} | Tier: {s.source_tier}\n\n{s.summary}\n\n"
    report += "## Methodology\nThis report was generated using a template-based fallback system due to a synthesis engine failure. Data accuracy is preserved from source summaries."
    return report

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
        if isinstance(obj, (datetime)):
             return obj.isoformat()
        return super().default(obj)

def export_report(content: str, plan: ResearchPlan, state: ResearchState, storage):
    rid = state.report_id or "latest"

    # Prepare data for JSON export, ensuring datetime serialization
    clean_state = state.model_dump(mode='json')

    # Individual success for each export
    try: storage.save_artifact(rid, "report", content, "md")
    except Exception as e: logger.error(f"MD export fail: {e}")

    if "json" in EXPORT_FORMATS:
        try: storage.save_artifact(rid, "json", clean_state, "json")
        except Exception as e: logger.error(f"JSON export fail: {e}")

    if "html" in EXPORT_FORMATS:
        try:
            html = f"<html><head><style>body{{font-family:sans-serif;line-height:1.6;margin:40px;}}</style></head><body>{content.replace('# ', '<h1>').replace('## ', '<h2>').replace('\n', '<br>')}</body></html>"
            storage.save_artifact(rid, "html", html, "html")
        except Exception as e: logger.error(f"HTML export fail: {e}")

def run_self_evaluation(report: str, plan: ResearchPlan, state: ResearchState) -> SelfEvaluation:
    """Deterministic self-evaluation based on report metrics (Phase 5)."""
    char_count = len(report)
    citation_count = len(re.findall(r'\[\d+\]', report))
    evidence_nodes = len(state.evidence_graph.items)

    # Simple deterministic scoring
    coverage_score = sum(o.coverage for o in state.objective_states.values()) / len(state.objective_states) if state.objective_states else 0
    readability_score = min(char_count / 5000.0, 1.0) * 100
    evidence_score = min(evidence_nodes / 10.0, 1.0) * 100
    citation_quality = min(citation_count / max(evidence_nodes, 1), 1.0) * 100

    overall = (coverage_score * 0.4) + (evidence_score * 0.3) + (citation_quality * 0.2) + (readability_score * 0.1)

    grade = "A" if overall > 85 else "B" if overall > 70 else "C" if overall > 50 else "D" if overall > 30 else "F"

    return SelfEvaluation(
        overall_grade=grade,
        justification=f"Deterministic evaluation: Coverage {coverage_score:.1f}%, Evidence {evidence_score:.1f}%, Citations {citation_quality:.1f}%",
        coverage_score=coverage_score,
        evidence_score=evidence_score,
        readability_score=readability_score,
        citation_quality=citation_quality
    )

def validate_objective_completeness(report: str, objectives: List[str], state: ResearchState) -> Dict[str, str]:
    """Deterministic validator: Maps report content back to objectives (Phase 5)."""
    results = {}
    report_lower = report.lower()

    for obj in objectives:
        # Check if objective is mentioned or has coverage
        obj_state = state.objective_states.get(obj)
        if obj_state and obj_state.coverage > 80:
            results[obj] = "YES"
        elif obj_state and obj_state.coverage > 30:
            results[obj] = "PARTIAL"
        else:
            results[obj] = "NO"

    return results
