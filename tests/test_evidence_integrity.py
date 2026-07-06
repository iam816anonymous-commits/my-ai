import unittest
from web_research_agent.tools.extractor import validate_semantic_relevance
from web_research_agent.models.llm import LLMClient

class TestEvidenceIntegrity(unittest.TestCase):
    def setUp(self):
        self.llm_client = LLMClient()

    def test_semantic_rejection_unrelated(self):
        """Verify that unrelated content is rejected."""
        query = "Latest trends in AI chip architecture"
        junk_text = "Check out my new video about baking cookies! Subscribe for more recipes."

        is_relevant = validate_semantic_relevance(junk_text, query, self.llm_client)
        self.assertFalse(is_relevant, "Unrelated baking content should be rejected for an AI chip query.")

    def test_semantic_acceptance_related(self):
        """Verify that related content is accepted."""
        query = "Latest trends in AI chip architecture"
        relevant_text = "NVIDIA and AMD are pushing the boundaries of HBM3 memory integration in their latest Blackwell and MI300X chip architectures."

        is_relevant = validate_semantic_relevance(relevant_text, query, self.llm_client)
        self.assertTrue(is_relevant, "Highly relevant technical content should be accepted.")

if __name__ == "__main__":
    unittest.main()
