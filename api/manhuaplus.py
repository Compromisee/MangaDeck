"""
ManhuaPlus adapter for Manhua (Chinese comics) support.
Scrapes manhuaplus.com
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from api.base import BaseAPI


class ManhuaPlusAPI(BaseAPI):
    SOURCE_NAME = "manhuaplus"
    BASE_URL = "https://manhuaplus.com"
    RATE_LIMIT = 1.0
    SUPPORTS_MANHUA = True
    SUPPORTS_MANHWA = False
    SUPPORTS_MANGA = False

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        params = {"s": query, "post_type": "wp-manga"}
        if page > 1:
            params["paged"] = page

        resp = self._get(self.BASE_URL, params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        items = soup.select(
            ".c-tabs-item__content, .row.c-tabs-item__content"
        )
        for item in items:
            link = item.select_one("a")
            if not link:
                continue

            href = link.get("href", "")
            title_el = item.select_one(
                ".post-title a, h3 a, h4 a"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            img = item.select_one("img")
            cover_url = ""
            if img:
                cover_url = (
                    img.get("data-src")
                    or img.get("src")
                    or img.get("data-lazy-src")
                    or ""
                )

            manga_id = self._url_to_id(href)

            results.append({
                "id": f"mhp_{manga_id}",
                "source_id": manga_id,
                "title": title,
                "alt_titles": [],
                "cover_url": cover_url,
                "source": self.SOURCE_NAME,
                "language": "en",
                "status": "unknown",
                "type": "manhua",
                "description": "",
                "authors": [],
                "genres": [],
                "chapter_count": None,
                "year": None,
                "url": href,
                "reading_direction": "vertical",
            })

        return results

    def _url_to_id(self, url):
        match = re.search(r'/manga/([^/]+)', url)
        if match:
            return match.group(1)
        return url.rstrip("/").split("/")[-1]

    def _id_to_url(self, manga_id):
        source_id = manga_id
        if manga_id.startswith("mhp_"):
            source_id = manga_id[4:]
        return f"{self.BASE_URL}/manga/{source_id}/"

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one(
            ".post-title h1, .post-title h3"
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown"

        cover_el = soup.select_one(
            ".summary_image img, .tab-summary img"
        )
        cover_url = ""
        if cover_el:
            cover_url = (
                cover_el.get("data-src")
                or cover_el.get("src")
                or ""
            )

        desc_el = soup.select_one(
            ".summary__content p, .description-summary p, "
            "div.summary__content"
        )
        description = desc_el.get_text(strip=True)[:500] if desc_el else ""

        authors = []
        for a in soup.select(".author-content a"):
            authors.append(a.get_text(strip=True))

        genres = []
        for a in soup.select(".genres-content a"):
            genres.append(a.get_text(strip=True))

        status = "unknown"
        status_el = soup.select_one(
            ".post-status .summary-content, "
            ".post-content_item:contains('Status') .summary-content"
        )
        if status_el:
            st = status_el.get_text(strip=True).lower()
            if "ongoing" in st:
                status = "ongoing"
            elif "completed" in st:
                status = "completed"

        chapters = self.get_chapters(manga_id)

        source_id = manga_id
        if manga_id.startswith("mhp_"):
            source_id = manga_id[4:]

        return {
            "id": f"mhp_{source_id}",
            "source_id": source_id,
            "title": title,
            "alt_titles": [],
            "cover_url": cover_url,
            "source": self.SOURCE_NAME,
            "language": "en",
            "status": status,
            "type": "manhua",
            "description": description,
            "authors": authors,
            "genres": genres,
            "chapter_count": len(chapters),
            "year": None,
            "url": url,
            "reading_direction": "vertical",
            "chapters": chapters,
            "volumes": {},
            "related": [],
        }

    def get_chapters(
        self, manga_id: str, language: str = "en"
    ) -> List[Dict]:
        url = self._id_to_url(manga_id)
        # Madara theme uses AJAX for chapter list
        ajax_url = url.rstrip("/") + "/ajax/chapters/"
        resp = self._get(url)
        if not resp:
            return []

        # Try AJAX endpoint first
        ajax_resp = None
        try:
            self._rate_limit()
            ajax_resp = self._session.post(
                ajax_url,
                headers={"Referer": url, "X-Requested-With": "XMLHttpRequest"},
                timeout=30,
            )
        except Exception:
            pass

        if ajax_resp and ajax_resp.status_code == 200:
            soup = BeautifulSoup(ajax_resp.text, "html.parser")
        else:
            soup = BeautifulSoup(resp.text, "html.parser")

        chapters = []
        seen = set()

        links = soup.select(
            ".wp-manga-chapter a, "
            "li.wp-manga-chapter a, "
            "a[href*='chapter']"
        )

        for el in links:
            href = el.get("href", "")
            if not href or href in seen:
                continue

            ch_match = re.search(r'[Cc]hapter[_\s-]*([\d.]+)', href)
            if not ch_match:
                ch_match = re.search(
                    r'[Cc]hapter\s*([\d.]+)', el.get_text()
                )
            if not ch_match:
                continue

            try:
                ch_num = float(ch_match.group(1))
            except ValueError:
                continue

            seen.add(href)
            text = el.get_text(strip=True)
            ch_id = self.generate_id(self.SOURCE_NAME, manga_id, ch_num)

            chapters.append({
                "id": f"mhp_{ch_id}",
                "source_id": href,
                "chapter_number": ch_num,
                "volume_number": None,
                "title": text,
                "language": "en",
                "pages": None,
                "source": self.SOURCE_NAME,
                "url": href,
                "date": None,
                "scanlation_group": None,
            })

        chapters.sort(key=lambda c: c["chapter_number"])
        return chapters

    def get_chapter_images(self, chapter_id: str) -> List[str]:
        url = chapter_id
        if chapter_id.startswith("mhp_"):
            url = chapter_id[4:]

        if not url.startswith("http"):
            return []

        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        images = []

        container = soup.select_one(
            ".reading-content, .chapter-content, .entry-content"
        )
        if container:
            for img in container.select("img"):
                src = (
                    img.get("data-src")
                    or img.get("src")
                    or img.get("data-lazy-src")
                )
                if src:
                    src = src.strip()
                    if src.startswith("http"):
                        images.append(src)

        if not images:
            for img in soup.select("img.wp-manga-chapter-img"):
                src = img.get("data-src") or img.get("src")
                if src:
                    images.append(src.strip())

        return images