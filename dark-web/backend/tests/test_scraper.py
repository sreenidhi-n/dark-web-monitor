"""Unit tests for OnionScraper — no network, no DB, no Tor needed."""

from unittest.mock import MagicMock

import pytest

from app.crawler.scraper import OnionScraper

SIMPLE_HTML = """
<html>
  <head><title>  Test Page  </title></head>
  <body>
    <script>alert('should be removed')</script>
    <style>.hidden { display:none }</style>
    <p>Acme Corp leaked credentials found here.</p>
    <a href="http://other.onion/page">Link</a>
    <a href="/relative">Relative</a>
  </body>
</html>
"""


def _make_scraper(html: str = SIMPLE_HTML, status: int = 200) -> OnionScraper:
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.status_code = status
    mock_resp.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    return OnionScraper(mock_session)


class TestComputeHash:
    def test_deterministic(self):
        h1 = OnionScraper.compute_hash("hello world")
        h2 = OnionScraper.compute_hash("hello world")
        assert h1 == h2

    def test_different_content_different_hash(self):
        assert OnionScraper.compute_hash("a") != OnionScraper.compute_hash("b")

    def test_sha256_length(self):
        assert len(OnionScraper.compute_hash("anything")) == 64


class TestKeywordMatches:
    def setup_method(self):
        self.scraper = _make_scraper()

    def test_case_insensitive_match(self):
        matches = self.scraper.extract_keyword_matches("Acme Corp leaked data", ["acme", "corp"])
        assert set(matches) == {"acme", "corp"}

    def test_no_match(self):
        matches = self.scraper.extract_keyword_matches("nothing relevant here", ["secret"])
        assert matches == []

    def test_partial_word_matches(self):
        # "acmecorp" contains "acme" as a substring
        matches = self.scraper.extract_keyword_matches("visit acmecorp.com", ["acme"])
        assert "acme" in matches


class TestParse:
    def test_title_extracted(self):
        scraper = _make_scraper()
        result = scraper.scrape("http://test.onion")
        assert result["title"] == "Test Page"

    def test_scripts_stripped(self):
        scraper = _make_scraper()
        result = scraper.scrape("http://test.onion")
        assert "alert(" not in result["text"]
        assert ".hidden" not in result["text"]

    def test_content_hash_present(self):
        scraper = _make_scraper()
        result = scraper.scrape("http://test.onion")
        assert len(result["content_hash"]) == 64

    def test_absolute_links_collected(self):
        scraper = _make_scraper()
        result = scraper.scrape("http://test.onion")
        assert "http://other.onion/page" in result["links"]

    def test_relative_links_resolved(self):
        scraper = _make_scraper()
        result = scraper.scrape("http://test.onion")
        assert "http://test.onion/relative" in result["links"]

    def test_error_returns_error_dict(self):
        mock_session = MagicMock()
        mock_session.get.side_effect = ConnectionError("Tor circuit failed")
        scraper = OnionScraper(mock_session)
        result = scraper.scrape("http://unreachable.onion")
        assert result["error"] is not None
        assert result["status_code"] is None
