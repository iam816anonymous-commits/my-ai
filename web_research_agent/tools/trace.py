import json
from pathlib import Path
from typing import Any
from web_research_agent.models.schemas import ResearchState
from web_research_agent.config import OUTPUT_DIR

def generate_research_trace(state: ResearchState) -> str:
    """
    Generates a Markdown trace of the research process.
    """
    trace = [
        f"# Research Trace: {state.query}",
        f"Started: {state.start_time.isoformat()}",
        f"Iterations: {state.iterations}",
        "",
        "## Research Objectives",
        "\n".join([f"- {obj}" for obj in (state.plan.objectives if state.plan else [])]),
        "",
        "## Search Summary",
        f"- URLs Discovered: {state.urls_found}",
        f"- URLs Rejected: {len(state.urls_rejected)}",
        "",
        "### Rejection Log",
    ]

    for rej in state.urls_rejected:
        trace.append(f"- **{rej.url}**: {rej.rejection_reason} (Score: {rej.score})")

    trace.extend([
        "",
        "## Confidence Evolution",
        " -> ".join([str(c) for i, c in enumerate(state.confidence_evolution)]),
        "",
        "## Final Reasoning Decisions",
        json.dumps(state.objective_coverage, indent=2),
        "",
        "## Evidence Graph Snapshot",
    ])

    for item in state.evidence_graph.items:
        trace.append(f"- **Claim**: {item.claim}")
        trace.append(f"  Strength: {item.evidence_strength} | Sources: {', '.join(item.supporting_sources)}")

    return "\n".join(trace)

def save_trace_artifacts(state: ResearchState):
    """Saves trace.md and profiling.json."""
    trace_md = generate_research_trace(state)
    with open(OUTPUT_DIR / "trace.md", "w") as f:
        f.write(trace_md)

    profiling_data = state.profiling.model_dump()
    with open(OUTPUT_DIR / "profiling.json", "w") as f:
        json.dump(profiling_data, f, indent=2)
