"""
MangaKakalot adapter.
Scrapes mangakakalot.com
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from api.base import BaseAPI


class MangaKakalotAPI(BaseAPI):
    SOURCE_NAME = "mangakakalot"
    BASE_URL = "https://mangakakalot.com"
    RATE_LIMIT = 1.0
    SUPPORTS_MANHUA = True
    SUPPORTS_MANHWA = True

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        search_query = query.replace(" ", "_")
        url = f"{self.BASE_URL}/search/story/{search_query}"
        if page > 1:
            url += f"?page={page}"

        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        items = soup.select(".story_item, .search-story-item")
        for item in items:
            link = item.select_one("a")
            if not link:
                continue

            href = link.get("href", "")
            img = item.select_one("img")
            cover_url = img.get("src", "") if img else ""

            title_el = item.select_one("h3 a, .story_name a, .item-title")
            title = title_el.get_text(strip=True) if title_el else ""

            if not title:
                title = link.get("title", "") or link.get_text(strip=True)

            manga_id = self._url_to_id(href)

            results.append({
                "id": f"mkk_{manga_id}",
                "source_id": manga_id,
                "title": title,
                "alt_titles": [],
                "cover_url": cover_url,
                "source": self.SOURCE_NAME,
                "language": "en",
                "status": "unknown",
                "type": "manga",
                "description": "",
                "authors": [],
                "genres": [],
                "chapter_count": None,
                "year": None,
                "url": href,
                "reading_direction": "rtl",
            })

        return results

    def _url_to_id(self, url):
        slug = url.rstrip("/").split("/")[-1]
        return slug

    def _id_to_url(self, manga_id):
        source_id = manga_id
        if manga_id.startswith("mkk_"):
            source_id = manga_id[4:]
        if source_id.startswith("manga-"):
            return f"https://chapmanganato.to/{source_id}"
        if source_id.startswith("read-"):
            return f"{self.BASE_URL}/{source_id}"
        return f"{self.BASE_URL}/manga/{source_id}"

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one(
            "h1, .manga-info-text h1, .story-info-right h1"
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown"

        cover_el = soup.select_one(
            ".manga-info-pic img, .info-image img"
        )
        cover_url = cover_el.get("src", "") if cover_el else ""

        desc_el = soup.select_one(
            "#noidungm, #panel-story-info-description, .panel-story-info-description"
        )
        description = ""
        if desc_el:
            description = desc_el.get_text(strip=True)[:500]

        authors = []
        genres = []
        status = "unknown"

        info_items = soup.select(
            ".manga-info-text li, .variations-tableInfo tr"
        )
        for item in info_items:
            text = item.get_text(strip=True).lower()
            if "author" in text:
                for a in item.select("a"):
                    authors.append(a.get_text(strip=True))
            elif "genre" in text:
                for a in item.select("a"):
                    genres.append(a.get_text(strip=True))
            elif "status" in text:
                if "ongoing" in text:
                    status = "ongoing"
                elif "completed" in text:
                    status = "completed"

        m_type = "manga"
        for g in genres:
            gl = g.lower()
            if "manhua" in gl:
                m_type = "manhua"
            elif "manhwa" in gl:
                m_type = "manhwa"

        chapters = self.get_chapters(manga_id)

        source_id = manga_id
        if manga_id.startswith("mkk_"):
            source_id = manga_id[4:]

        return {
            "id": f"mkk_{source_id}",
            "source_id": source_id,
            "title": title,
            "alt_titles": [],
            "cover_url": cover_url,
            "source": self.SOURCE_NAME,
            "language": "en",
            "status": status,
            "type": m_type,
            "description": description,
            "authors": authors,
            "genres": genres,
            "chapter_count": len(chapters),
            "year": None,
            "url": url,
            "reading_direction": "rtl" if m_type == "manga" else "vertical",
            "chapters": chapters,
            "volumes": {},
            "related": [],
        }

    def get_chapters(
        self, manga_id: str, language: str = "en"
    ) -> List[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        chapters = []
        seen = set()

        links = soup.select(
            ".chapter-list .row a, "
            ".row-content-chapter li a, "
            "a[href*='chapter']"
        )

        for el in links:
            href = el.get("href", "")
            if not href or href in seen:
                continue

            ch_match = re.search(r'[Cc]hapter[_\s-]*([\d.]+)', href)
            if not ch_match:
                ch_match = re.search(r'[Cc]hapter\s*([\d.]+)', el.get_text())
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
                "id": f"mkk_{ch_id}",
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
        if chapter_id.startswith("mkk_"):
            url = chapter_id[4:]

        if not url.startswith("http"):
            return []

        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        images = []

        container = soup.select_one(
            "#vungdoc, .container-chapter-reader, .vung-doc"
        )
        if container:
            for img in container.select("img"):
                src = img.get("src") or img.get("data-src")
                if src and src.startswith("http"):
                    images.append(src)

        if not images:
            for img in soup.select("img"):
                src = img.get("src", "")
                if re.search(r'\.(jpg|jpeg|png|webp)', src, re.I):
                    if any(
                        kw in src
                        for kw in ["chapter", "manga", "page", "img"]
                    ):
                        images.append(src)

        return images

    def download_image(self, url: str, headers=None) -> Optional[bytes]:
        h = {"Referer": self.BASE_URL + "/"}
        if headers:
            h.update(headers)
        return super().download_image(url, headers=h)