"""
Webtoon (LINE Webtoon) adapter.
Uses webtoon.com endpoints.
"""

import re
import json
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from api.base import BaseAPI


class WebtoonAPI(BaseAPI):
    SOURCE_NAME = "webtoon"
    BASE_URL = "https://www.webtoons.com"
    RATE_LIMIT = 1.0
    SUPPORTS_MANHWA = True
    SUPPORTS_MANHUA = False
    SUPPORTS_MANGA = False

    LANG_MAP = {
        "en": "en",
        "ko": "ko",
        "zh": "zh-hant",
        "ja": "ja",
        "th": "th",
        "id": "id",
        "es": "es",
        "fr": "fr",
        "de": "de",
    }

    def _map_lang(self, lang):
        return self.LANG_MAP.get(lang, "en")

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        lang = self._map_lang(language)
        params = {
            "keyword": query,
            "searchType": "WEBTOON",
            "page": page,
        }
        url = f"{self.BASE_URL}/{lang}/search"
        resp = self._get(url, params=params, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        items = soup.select(
            ".card_lst li, .search_lst li, ._searchResultItem"
        )
        for item in items:
            link = item.select_one("a")
            if not link:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                href = self.BASE_URL + href

            img = item.select_one("img")
            cover_url = ""
            if img:
                cover_url = img.get("src") or img.get("data-src") or ""

            title_el = item.select_one(
                ".subj, .info .subj, p.subj"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            if not title and img:
                title = img.get("alt", "")

            author_el = item.select_one(".author, .info .author")
            authors = []
            if author_el:
                authors = [author_el.get_text(strip=True)]

            genre_el = item.select_one(".genre, .info .genre")
            genres = []
            if genre_el:
                genres = [genre_el.get_text(strip=True)]

            # Extract title_no from URL
            title_no_match = re.search(r'title_no=(\d+)', href)
            manga_id = title_no_match.group(1) if title_no_match else self.generate_id(href)

            results.append({
                "id": f"wt_{manga_id}",
                "source_id": manga_id,
                "title": title,
                "alt_titles": [],
                "cover_url": cover_url,
                "source": self.SOURCE_NAME,
                "language": language,
                "status": "unknown",
                "type": "manhwa",
                "description": "",
                "authors": authors,
                "genres": genres,
                "chapter_count": None,
                "year": None,
                "url": href,
                "reading_direction": "vertical",
            })

        return results

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        source_id = manga_id
        if manga_id.startswith("wt_"):
            source_id = manga_id[3:]

        # Need to find the actual URL - search for it or construct
        url = f"{self.BASE_URL}/en/search?keyword={source_id}"
        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return None

        # Try to find direct manga page
        soup = BeautifulSoup(resp.text, "html.parser")

        title = "Unknown"
        cover_url = ""
        description = ""
        authors = []
        genres = []

        title_el = soup.select_one("h1.subj, .detail_header .subj, h3.subj")
        if title_el:
            title = title_el.get_text(strip=True)

        cover_el = soup.select_one(".detail_body .thmb img, .info img")
        if cover_el:
            cover_url = cover_el.get("src") or ""

        desc_el = soup.select_one(".summary, p.summary")
        if desc_el:
            description = desc_el.get_text(strip=True)[:500]

        chapters = self.get_chapters(manga_id)

        return {
            "id": f"wt_{source_id}",
            "source_id": source_id,
            "title": title,
            "alt_titles": [],
            "cover_url": cover_url,
            "source": self.SOURCE_NAME,
            "language": "en",
            "status": "unknown",
            "type": "manhwa",
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
        source_id = manga_id
        if manga_id.startswith("wt_"):
            source_id = manga_id[3:]

        lang = self._map_lang(language)
        chapters = []
        page = 1

        while True:
            url = (
                f"{self.BASE_URL}/{lang}/xxx/list?"
                f"title_no={source_id}&page={page}"
            )
            resp = self._get(url, headers={"Referer": self.BASE_URL})
            if not resp:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            episode_list = soup.select("#_listUl li a, ._episodeItem a")

            if not episode_list:
                break

            for el in episode_list:
                href = el.get("href", "")
                if not href:
                    continue

                ep_match = re.search(r'episode_no=(\d+)', href)
                if not ep_match:
                    continue

                ep_no = int(ep_match.group(1))

                title_el = el.select_one(
                    ".subj span, .episode_title, .sub_title"
                )
                title = title_el.get_text(strip=True) if title_el else f"Episode {ep_no}"

                if not href.startswith("http"):
                    href = self.BASE_URL + href

                ch_id = self.generate_id(self.SOURCE_NAME, source_id, ep_no)
                chapters.append({
                    "id": f"wt_{ch_id}",
                    "source_id": href,
                    "chapter_number": float(ep_no),
                    "volume_number": None,
                    "title": title,
                    "language": language,
                    "pages": None,
                    "source": self.SOURCE_NAME,
                    "url": href,
                    "date": None,
                    "scanlation_group": "LINE Webtoon",
                })

            # Check if next page exists
            next_btn = soup.select_one("a.pg_next, .paginate a[href*='page=']")
            if not next_btn:
                break
            page += 1
            if page > 50:  # Safety limit
                break

        chapters.sort(key=lambda c: c["chapter_number"])
        return chapters

    def get_chapter_images(self, chapter_id: str) -> List[str]:
        url = chapter_id
        if chapter_id.startswith("wt_"):
            url = chapter_id[3:]

        if not url.startswith("http"):
            return []

        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        images = []

        viewer = soup.select_one("#_imageList, #content, .viewer_img")
        if viewer:
            for img in viewer.select("img"):
                src = img.get("data-url") or img.get("src") or img.get("data-src")
                if src and src.startswith("http"):
                    images.append(src)

        if not images:
            for img in soup.select("img[data-url]"):
                src = img.get("data-url")
                if src:
                    images.append(src)

        return images

    def download_image(self, url: str, headers=None) -> Optional[bytes]:
        h = {"Referer": "https://www.webtoons.com/"}
        if headers:
            h.update(headers)
        return super().download_image(url, headers=h)