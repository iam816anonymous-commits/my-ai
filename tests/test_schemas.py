import unittest
from web_research_agent.models.schemas import ResearchState, ResearchPlan, QueryIntent, ReasoningResult, ConfidenceBreakdown, ArticleSummary

class TestSchemaCompatibility(unittest.TestCase):
    def test_research_state_assignments(self):
        """Verifies that all fields used in researcher.py exist in ResearchState."""
        state = ResearchState(query="test")

        # Test assignments found in grep
        state.plan = ResearchPlan(topic="test", intent=QueryIntent.GENERAL, queries=[], objectives=[])
        state.iterations = 1
        state.urls_found = 1
        state.urls_rejected = []
        state.sources_collected = ["url1"]
        state.successful_downloads = 1
        state.successful_extractions = 1
        state.successful_summaries = 1

        state.objective_coverage = {"obj1": 90.0}
        state.follow_up_queries = ["q1"]
        state.summaries = [ArticleSummary(url="url1", summary="summary1")]

        breakdown = ConfidenceBreakdown(
            overall=80.0, coverage=90.0, evidence_strength=70.0,
            source_diversity=80.0, agreement=85.0, extraction_quality=95.0,
            missing_evidence_penalty=0.0, contradiction_penalty=0.0
        )
        state.confidence_breakdown = breakdown
        state.confidence_evolution = [80.0]

    def test_reasoning_result_mapping(self):
        """Verifies ReasoningResult structure."""
        res = ReasoningResult(
            completed_objectives=[],
            missing_objectives=[],
            objective_coverage={},
            continue_research=False
        )
        self.assertEqual(res.continue_research, False)

if __name__ == "__main__":
    unittest.main()
