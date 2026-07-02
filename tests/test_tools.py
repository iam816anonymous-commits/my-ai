import unittest
from web_research_agent.tools.search import get_source_info, normalize_url
from web_research_agent.tools.reasoner import calculate_confidence

class TestTools(unittest.TestCase):
    def test_source_scoring(self):
        score, stype = get_source_info("https://arxiv.org/abs/1234.5678")
        self.assertEqual(stype, "Research Paper")
        self.assertGreaterEqual(score, 100)

        score, stype = get_source_info("https://microsoft.com/docs/api")
        self.assertEqual(stype, "Official Documentation")

    def test_url_normalization(self):
        self.assertEqual(normalize_url("https://example.com/path/"), "https://example.com/path")
        self.assertEqual(normalize_url("https://example.com/path#frag"), "https://example.com/path")

    def test_confidence_calculation(self):
        state = {
            "objective_coverage": {"Obj 1": 100.0, "Obj 2": 80.0},
            "summaries": [{"url": "1"}, {"url": "2"}, {"url": "3"}],
            "contradictions": []
        }
        conf = calculate_confidence(state)
        # Expected: (90 * 0.6) + (3/8 * 100 * 0.2) + (100 * 0.2)
        # 54 + 7.5 + 20 = 81.5
        self.assertAlmostEqual(conf, 81.5, places=1)

if __name__ == "__main__":
    unittest.main()
