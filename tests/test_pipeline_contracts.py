import unittest
from web_research_agent.models.schemas import ResearchState, ObjectiveState, SourceDocument, PipelineResult, ObjectiveStatus, SourceV2Info

class TestPipelineContracts(unittest.TestCase):
    def test_pipeline_result_contract(self):
        # Every stage must emit a PipelineResult
        res = PipelineResult[str](success=True, payload="data", stage="test")
        self.assertTrue(res.success)
        self.assertEqual(res.payload, "data")

    def test_research_state_invariants(self):
        # ResearchState must initialize with default factories to prevent NoneType errors
        state = ResearchState(query="test query")
        self.assertIsInstance(state.visited_urls, list)
        self.assertIsInstance(state.objective_states, dict)
        self.assertEqual(state.iterations, 0)

    def test_source_document_contract(self):
        # Verify mandatory fields for SourceDocument (Module 8)
        doc = SourceDocument(
            id="123",
            url="https://example.com",
            clean_text="extracted text",
            summary="test summary"
        )
        self.assertEqual(doc.domain, "")
        self.assertEqual(len(doc.claims), 0)

    def test_search_v7_contract(self):
        from web_research_agent.tools.search import get_source_v7_info
        info = get_source_v7_info("https://example.com/test", "Test Page")
        self.assertIsInstance(info, SourceV2Info)
        self.assertEqual(info.url, "https://example.com/test")
        self.assertEqual(info.title, "Test Page")

if __name__ == "__main__":
    unittest.main()
