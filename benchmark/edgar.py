"""Talks to SEC EDGAR. Polite by construction: named User-Agent, paced requests, cached files."""
import json
import time

import requests

from .cache import Cache
from .config import EDGAR_PAUSE_SECONDS


class EdgarError(Exception):
    pass


def archive_url(cik: str, accession: str, filename: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{filename}"


def index_url(cik: str, accession: str) -> str:
    return archive_url(cik, accession, f"{accession}-index.htm")


class Edgar:
    def __init__(self, user_agent: str, cache: Cache | None, session_get=None, pause: float = EDGAR_PAUSE_SECONDS):
        if not user_agent or "@" not in user_agent:
            raise EdgarError("SEC_USER_AGENT must be set to a name and contact email, e.g. 'Jane Doe jane@firm.com'")
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.cache = cache
        self._get = session_get or requests.get
        self.pause = pause  # seconds between requests (config.EDGAR_PAUSE_SECONDS, with its source)
        self._last = 0.0

    def get_bytes(self, url: str) -> bytes:
        for attempt in range(4):
            wait = self.pause - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                resp = self._get(url, headers=self.headers, timeout=60)
            except requests.RequestException as exc:
                if attempt == 3:
                    raise EdgarError(f"Could not reach EDGAR ({url}): {exc}") from exc
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 200:
                return resp.content
            if resp.status_code == 403:
                raise EdgarError("EDGAR refused the request (403). This usually means a missing or invalid User-Agent: set SEC_USER_AGENT in .env to a real name and email.")
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise EdgarError(f"EDGAR returned HTTP {resp.status_code} for {url}")
        raise EdgarError(f"EDGAR request failed: {url}")

    def submissions(self, cik: str) -> dict:
        """Filing index for a company. Always refetched so new filings appear; a copy is cached."""
        content = self.get_bytes(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
        try:
            data = json.loads(content)
        except ValueError as exc:
            raise EdgarError(f"EDGAR returned an unreadable filing index for CIK {cik}") from exc
        if self.cache:
            self.cache.store(cik, "submissions", "submissions.json", content)
        return data

    def fetch(self, cik: str, accession: str, filename: str):
        """Path to a cached filing document, downloading it once if needed."""
        if not self.cache.has(cik, accession, filename):
            self.cache.store(cik, accession, filename, self.get_bytes(archive_url(cik, accession, filename)))
        return self.cache.path(cik, accession, filename)
