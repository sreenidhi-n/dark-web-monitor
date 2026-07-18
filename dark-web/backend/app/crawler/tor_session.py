import logging
import os

import requests
from stem import Signal
from stem.control import Controller

from app.config import settings

logger = logging.getLogger(__name__)

# When DIRECT_HTTP=true the session routes through the normal network stack
# instead of Tor — useful for testing with clearnet URLs locally.
_DIRECT_HTTP = os.getenv("DIRECT_HTTP", "false").lower() == "true"


class TorSession:
    def __init__(
        self,
        proxy_url: str = None,
        control_port: int = None,
        control_password: str = None,
    ):
        self.proxy_url = proxy_url or settings.tor_proxy
        self.control_port = control_port or settings.tor_control_port
        self.control_password = control_password or settings.tor_control_password
        self._request_count = 0
        self._session = self._build_session()
        if _DIRECT_HTTP:
            logger.warning("DIRECT_HTTP=true — Tor proxy disabled, using clearnet")

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        if not _DIRECT_HTTP:
            session.proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }
        # Mimic Tor Browser fingerprint to reduce detection surface
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
            }
        )
        return session

    def rotate_circuit(self) -> None:
        try:
            with Controller.from_port(port=self.control_port) as controller:
                if self.control_password:
                    controller.authenticate(password=self.control_password)
                else:
                    controller.authenticate()
                controller.signal(Signal.NEWNYM)
            logger.debug("Tor circuit rotated")
        except Exception as exc:
            # Non-fatal: log and continue with the existing circuit
            logger.warning("Circuit rotation failed: %s", exc)

    def get(self, url: str, **kwargs) -> requests.Response:
        self._request_count += 1
        if self._request_count % settings.circuit_rotate_every == 0:
            self.rotate_circuit()
        return self._session.get(url, timeout=settings.crawl_timeout, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._session.post(url, timeout=settings.crawl_timeout, **kwargs)

    def verify_tor(self) -> bool:
        """Return True if traffic is confirmed to be routing through Tor."""
        try:
            r = self._session.get("http://check.torproject.org/api/ip", timeout=15)
            return r.json().get("IsTor", False)
        except Exception as exc:
            logger.error("Tor verification failed: %s", exc)
            return False
