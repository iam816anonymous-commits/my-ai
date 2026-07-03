import unittest
from unittest.mock import MagicMock
import os
import json

# Dummy environment
os.environ["API_KEY"] = "sk-dummy"

from web_research_agent.agents.researcher import ResearchAgent
from web_research_agent.models.schemas import (
    ResearchPlan, ReasoningResult, ConfidenceBreakdown,
    ArticleSummary, QueryIntent, SelfEvaluation
)

class TestE2ESchema(unittest.TestCase):
    def test_pipeline_schema_integrity(self):
        """Simulates a pipeline run to check for any attribute or schema errors."""
        agent = ResearchAgent()

        # Mock LLM and search to return valid Pydantic-compatible data
        agent.llm_client.get_json = MagicMock()
        agent.llm_client.call = MagicMock(return_value="# Mock Report")

        # 1. Mock Plan
        agent.llm_client.get_json.side_effect = [
            # Planner
            {
                "topic": "test",
                "intent": "Technology",
                "queries": ["q1"],
                "objectives": ["obj1"]
            },
            # Reasoner
            {
                "completed_objectives": ["obj1"],
                "missing_objectives": [],
                "contradictions": [],
                "objective_coverage": {"obj1": 100.0},
                "evidence_items": [],
                "gaps": [],
                "follow_up_queries": [],
                "continue_research": False
            },
            # Self-Evaluation
            {
                "overall_grade": "A",
                "justification": "good",
                "coverage_score": 100.0,
                "evidence_score": 100.0,
                "readability_score": 100.0,
                "citation_quality": 100.0,
                "objectivity": 100.0,
                "bias_risk": 0.0,
                "novel_insights": 100.0
            }
        ]

        import web_research_agent.tools.search
        web_research_agent.tools.search.search_web = MagicMock(return_value=([{"url": "http://test.com", "score": 100, "source_type": "Research Paper"}], []))

        import web_research_agent.tools.browser
        web_research_agent.tools.browser.fetch_all = MagicMock(return_value={"http://test.com": "<html><body>test</body></html>"})

        import web_research_agent.tools.extractor
        web_research_agent.tools.extractor.extract_all = MagicMock(return_value={"http://test.com": "test content"})

        try:
            state, evaluation = agent.run("What is Web3?")
            self.assertIsInstance(evaluation, SelfEvaluation)
            print("E2E Schema Test Passed")
        except Exception as e:
            self.fail(f"Pipeline failed with schema/attribute error: {e}")

if __name__ == "__main__":
    unittest.main()
