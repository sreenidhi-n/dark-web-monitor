import hashlib
import logging
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.crawler.tor_session import TorSession

logger = logging.getLogger(__name__)

SNIPPET_MAX_CHARS = 500


class OnionScraper:
    def __init__(self, session: TorSession):
        self.session = session

    def scrape(self, url: str) -> dict:
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return self._parse(url, response.text, response.status_code)
        except Exception as exc:
            logger.warning("Failed to scrape %s: %s", url, exc)
            return {"url": url, "error": str(exc), "status_code": None}

    def _parse(self, url: str, html: str, status_code: int) -> dict:
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator=" ", strip=True)
        snippet = text[:SNIPPET_MAX_CHARS]

        base = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                links.append(urljoin(base, href))

        return {
            "url": url,
            "title": title,
            "text": text,
            "snippet": snippet,
            "links": list(set(links)),
            "content_hash": self.compute_hash(text),
            "status_code": status_code,
            "error": None,
        }

    def extract_keyword_matches(self, text: str, keywords: list[str]) -> list[str]:
        """Return the subset of keywords that appear in text (case-insensitive)."""
        lower = text.lower()
        return [kw for kw in keywords if kw.lower() in lower]

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
