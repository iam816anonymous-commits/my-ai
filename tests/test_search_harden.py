import os
import shutil
import unittest
import logging
from pathlib import Path
from web_research_agent.tools.search import search_web, canonicalize_url, get_source_v7_info
from web_research_agent.startup import initialize_directories
from web_research_agent.config import OUTPUT_DIR, LOGS_DIR, CACHE_DIR
from web_research_agent.models.schemas import SourceV2Info

# Disable logs during tests
logging.basicConfig(level=logging.CRITICAL)

class TestSearchHarden(unittest.TestCase):
    def test_canonicalization(self):
        url1 = "https://example.com/page?utm_source=test&id=123#frag"
        url2 = "https://example.com/page/?id=123"
        self.assertEqual(canonicalize_url(url1), "https://example.com/page?id=123")
        self.assertEqual(canonicalize_url(url2), "https://example.com/page?id=123")

    def test_source_v7_filtering(self):
        # Test social media filtering
        info = get_source_v7_info("https://twitter.com/someone/status/123")
        self.assertIsNotNone(info.rejection_reason)
        self.assertIn("Social", info.rejection_reason)

        # Test authoritative scoring
        info = get_source_v7_info("https://arxiv.org/abs/2101.00001")
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
        queries = ["site:arxiv.org 'large language models'", "site:github.com 'web_research_agent'"]
        res = search_web(queries, max_results_total=2)

        self.assertTrue(res.success)
        out = res.payload
        self.assertIsInstance(out.scored_urls, list)
        self.assertIsInstance(out.health, dict)
        self.assertIn("duckduckgo", out.health)

if __name__ == "__main__":
    unittest.main()
