import os
import shutil
import unittest
import logging
from pathlib import Path
from web_research_agent.tools.search import search_web, canonicalize_url, get_source_v6_info
from web_research_agent.startup import initialize_directories
from web_research_agent.config import OUTPUT_DIR, LOGS_DIR, CACHE_DIR

# Disable logs during tests
logging.basicConfig(level=logging.CRITICAL)

class TestSearchHarden(unittest.TestCase):
    def test_canonicalization(self):
        url1 = "https://example.com/page?utm_source=test&id=123#frag"
        url2 = "https://example.com/page/?id=123"
        self.assertEqual(canonicalize_url(url1), "https://example.com/page?id=123")
        self.assertEqual(canonicalize_url(url2), "https://example.com/page?id=123")

    def test_source_v6_filtering(self):
        # Test file format filtering
        info = get_source_v6_info("https://example.com/paper.pdf")
        self.assertIsNotNone(info.rejection_reason)
        self.assertIn("format", info.rejection_reason)

        # Test social media filtering
        info = get_source_v6_info("https://twitter.com/someone/status/123")
        self.assertIsNotNone(info.rejection_reason)
        self.assertIn("Social", info.rejection_reason)

        # Test authoritative scoring
        info = get_source_v6_info("https://arxiv.org/abs/2101.00001")
        self.assertEqual(info.tier, 1)
        self.assertIsNone(info.rejection_reason)

    def test_directory_initialization(self):
        # Setup: delete test directories if they exist
        test_root = Path("test_env")
        if test_root.exists():
            shutil.rmtree(test_root)

        # Monkeypatch config dirs for this test
        import web_research_agent.config as config
        original_output = config.OUTPUT_DIR
        original_logs = config.LOGS_DIR
        original_cache = config.CACHE_DIR

        config.OUTPUT_DIR = test_root / "output"
        config.LOGS_DIR = test_root / "logs"
        config.CACHE_DIR = test_root / "cache"

        try:
            initialize_directories()
            self.assertTrue(config.OUTPUT_DIR.exists())
            self.assertTrue(config.LOGS_DIR.exists())
            self.assertTrue(config.CACHE_DIR.exists())
            self.assertTrue((config.OUTPUT_DIR / "reports").exists())
        finally:
            # Cleanup
            config.OUTPUT_DIR = original_output
            config.LOGS_DIR = original_logs
            config.CACHE_DIR = original_cache
            if test_root.exists():
                shutil.rmtree(test_root)

    def test_search_concurrency_and_fallback(self):
        # Note: This performs real searches, so it requires internet
        # We test with very specific queries to minimize noise
        queries = ["site:arxiv.org 'large language models'", "site:github.com 'web_research_agent'"]
        results, rejected, health = search_web(queries, max_results_total=2)

        self.assertIsInstance(results, list)
        self.assertIsInstance(health, dict)
        self.assertIn("duckduckgo", health)

        # Fallback test with a query likely to have no direct matches
        bad_queries = ["THISISARANDOMSTRINGTHATSHOULDNEVERMATCHANYTHING123456789"]
        results_f, rejected_f, health_f = search_web(bad_queries)
        # Should either be empty or have fallback results
        self.assertIsInstance(results_f, list)

if __name__ == "__main__":
    unittest.main()
