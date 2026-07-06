import unittest
import logging
from web_research_agent.tools.extractor import extract_text_v2
from web_research_agent.tools.reasoner import calculate_production_confidence
from web_research_agent.models.schemas import ObjectiveStatus

class TestCoreModules(unittest.TestCase):
    def test_extractor_imports(self):
        # This will fail if 'time' or other modules are missing
        res = extract_text_v2("<html><body>Test</body></html>")
        self.assertIsInstance(res, str)

    def test_confidence_logic_basic(self):
        # Test zero evidence case
        res = calculate_production_confidence({})
        self.assertEqual(res.overall, 0.0)
        self.assertIn("Insufficient", res.status)

    def test_schemas_enum(self):
        self.assertEqual(ObjectiveStatus.COMPLETE.value, "COMPLETE")

if __name__ == "__main__":
    unittest.main()
