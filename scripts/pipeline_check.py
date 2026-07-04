import sys
from rich import print as rprint
from web_research_agent.models.schemas import ResearchState, ObjectiveState, ConfidenceBreakdown, ReasoningResult

def check_pipeline_contracts():
    """Validates that Pydantic models can be correctly instantiated with required fields."""
    try:
        # Check ResearchState invariants
        state = ResearchState(query="test query")
        assert state.iterations == 0
        assert isinstance(state.objective_states, dict)

        # Check ReasoningResult defaults
        res = ReasoningResult(continue_research=False)
        assert isinstance(res.objective_states, list)
        assert isinstance(res.confidence_breakdown, ConfidenceBreakdown)

        # Check ObjectiveState
        obj = ObjectiveState(objective="test obj")
        assert obj.coverage == 0.0

        rprint("[green]Pipeline contract validation passed.[/green]")
        return True
    except Exception as e:
        rprint(f"[bold red]ERROR: Pipeline contract validation failed: {e}[/bold red]")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_pipeline_contracts() else 1)
