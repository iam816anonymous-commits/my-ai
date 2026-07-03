import unittest
from web_research_agent.tools.search import get_source_v2_info
from web_research_agent.tools.reasoner import calculate_explainable_confidence

class TestTools(unittest.TestCase):
    def test_source_scoring_v2(self):
        info = get_source_v2_info("https://arxiv.org/abs/1234.5678")
        self.assertEqual(info.type, "Research Paper")
        self.assertGreaterEqual(info.score, 100)

        info = get_source_v2_info("https://microsoft.com/docs/api")
        self.assertEqual(info.type, "Official Documentation")

    def test_explainable_confidence(self):
        state = {
            "objective_coverage": {"Obj 1": 100.0, "Obj 2": 80.0},
            "summaries": [{"url": "http://test.com", "quality_score": 90}],
            "contradictions": []
        }
        breakdown = calculate_explainable_confidence(state)
        self.assertGreater(breakdown.overall, 0)
        self.assertEqual(breakdown.coverage, 90.0)

if __name__ == "__main__":
    unittest.main()
