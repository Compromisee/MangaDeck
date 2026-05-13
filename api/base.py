"""
Base API class for all manga source adapters.
All sources must implement these methods.
"""

import requests
import time
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from urllib.parse import urljoin


class BaseAPI(ABC):
    """Abstract base for every manga source adapter."""

    SOURCE_NAME = "unknown"
    BASE_URL = ""
    RATE_LIMIT = 0.5  # seconds between requests
    SUPPORTS_MANHUA = False
    SUPPORTS_MANHWA = False
    SUPPORTS_MANGA = True

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._last_request_time = 0
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/json,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        rate = self.config.get("rate_limit_delay", None)
        if rate is not None:
            self.RATE_LIMIT = float(rate)

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request_time = time.time()

    def _get(self, url, params=None, headers=None, timeout=30):
        """Rate-limited GET request."""
        self._rate_limit()
        try:
            merged_headers = dict(self._session.headers)
            if headers:
                merged_headers.update(headers)
            resp = self._session.get(
                url, params=params, headers=merged_headers, timeout=timeout
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout:
            self.logger.warning(f"[{self.SOURCE_NAME}] Timeout: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"[{self.SOURCE_NAME}] HTTP {e.response.status_code}: {url}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"[{self.SOURCE_NAME}] Request error: {e}")
            return None

    def _get_json(self, url, params=None, headers=None, timeout=30):
        """Rate-limited GET request returning JSON."""
        resp = self._get(url, params=params, headers=headers, timeout=timeout)
        if resp is None:
            return None
        try:
            return resp.json()
        except ValueError:
            self.logger.warning(f"[{self.SOURCE_NAME}] Invalid JSON from {url}")
            return None

    def generate_id(self, *parts):
        """Generate a deterministic ID from parts."""
        raw = "|".join(str(p) for p in parts)
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @abstractmethod
    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        """
        Search for manga. Returns list of:
        {
            "id": str,
            "source_id": str,       # ID within this source
            "title": str,
            "alt_titles": [str],
            "cover_url": str,
            "source": str,          # SOURCE_NAME
            "language": str,
            "status": str,          # ongoing, completed, hiatus, unknown
            "type": str,            # manga, manhua, manhwa
            "description": str,
            "authors": [str],
            "genres": [str],
            "chapter_count": int or None,
            "year": int or None,
            "url": str,
        }
        """
        pass

    @abstractmethod
    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        """
        Get full details for a manga. Returns:
        {
            ...same as search result...,
            "chapters": [...],
            "volumes": {...},
            "reading_direction": "rtl" | "ltr" | "vertical",
            "related": [...]
        }
        """
        pass

    @abstractmethod
    def get_chapters(
        self, manga_id: str, language: str = "en"
    ) -> List[Dict]:
        """
        Get chapter list. Returns list of:
        {
            "id": str,
            "source_id": str,
            "chapter_number": float,
            "volume_number": float or None,
            "title": str,
            "language": str,
            "pages": int or None,
            "source": str,
            "url": str,
            "date": str or None,
            "scanlation_group": str or None,
        }
        """
        pass

    @abstractmethod
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        """Get list of image URLs for a chapter."""
        pass

    def get_cover(self, manga_id: str) -> Optional[str]:
        """Get cover image URL. Default implementation returns None."""
        details = self.get_manga_details(manga_id)
        if details:
            return details.get("cover_url")
        return None

    def get_volumes(
        self, manga_id: str, language: str = "en"
    ) -> Dict[str, List[Dict]]:
        """
        Group chapters by volume. Returns:
        { "1": [chapter_dicts], "2": [...], "none": [...] }
        """
        chapters = self.get_chapters(manga_id, language)
        volumes = {}
        for ch in chapters:
            vol = ch.get("volume_number")
            key = str(int(vol)) if vol and vol == int(vol) else (
                str(vol) if vol else "none"
            )
            volumes.setdefault(key, []).append(ch)
        for key in volumes:
            volumes[key].sort(key=lambda c: c.get("chapter_number", 0))
        return volumes

    def download_image(self, url: str, headers: Optional[Dict] = None) -> Optional[bytes]:
        """Download a single image. Returns bytes or None."""
        resp = self._get(url, headers=headers, timeout=60)
        if resp and resp.status_code == 200:
            return resp.content
        return None

    def is_available(self) -> bool:
        """Check if the source is reachable."""
        try:
            resp = self._get(self.BASE_URL, timeout=10)
            return resp is not None
        except Exception:
            return False

    def get_trending(self, language: str = "en", page: int = 1) -> List[Dict]:
        """Get trending/popular manga. Default returns empty list."""
        return []

    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        return ["en"]