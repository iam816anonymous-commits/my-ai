import unittest
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestStartup(unittest.TestCase):
    def test_imports(self):
        """Verifies that all major modules can be imported without error."""
        try:
            import web_research_agent.config
            import web_research_agent.models.schemas
            import web_research_agent.models.llm
            import web_research_agent.tools.browser
            import web_research_agent.tools.extractor
            import web_research_agent.tools.planner
            import web_research_agent.tools.reasoner
            import web_research_agent.tools.reporter
            import web_research_agent.tools.search
            import web_research_agent.tools.trace
            import web_research_agent.agents.researcher
            import web_research_agent.main
        except ImportError as e:
            self.fail(f"Import failed: {e}")
        except Exception as e:
            self.fail(f"An unexpected error occurred during import: {e}")

if __name__ == "__main__":
    unittest.main()
