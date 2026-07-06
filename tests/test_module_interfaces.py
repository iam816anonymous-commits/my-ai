import unittest
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

class TestModuleInterfaces(unittest.TestCase):
    def test_interfaces_stable(self):
        """Regression test to prevent breaking public APIs."""
        from web_research_agent.tools.interface_validator import validate_module_interfaces
        self.assertTrue(validate_module_interfaces(), "Module interface drift detected. See console output.")

if __name__ == "__main__":
    unittest.main()
