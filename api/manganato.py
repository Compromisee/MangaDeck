"""
Manganato/Chapmanganato adapter.
Scrapes manganato.com / chapmanganato.to
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from api.base import BaseAPI


class ManganatoAPI(BaseAPI):
    SOURCE_NAME = "manganato"
    BASE_URL = "https://manganato.com"
    SEARCH_URL = "https://manganato.com/search/story"
    RATE_LIMIT = 1.0
    SUPPORTS_MANHUA = True
    SUPPORTS_MANHWA = True

    def _referer_headers(self, url=""):
        return {"Referer": url or self.BASE_URL}

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        search_query = query.replace(" ", "_")
        url = f"{self.SEARCH_URL}/{search_query}"
        if page > 1:
            url += f"?page={page}"

        resp = self._get(url, headers=self._referer_headers())
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        items = soup.select(".search-story-item, .content-genres-item")
        for item in items:
            link = item.select_one("a.item-img, a.genres-item-img")
            if not link:
                continue

            href = link.get("href", "")
            img = link.select_one("img")
            cover_url = img.get("src", "") if img else ""

            title_el = item.select_one("h3 a, .item-title, a.item-title")
            if not title_el:
                title_el = link
            title = title_el.get_text(strip=True)

            authors = []
            author_el = item.select_one(".item-author, span.text-nowrap")
            if author_el:
                authors = [
                    a.strip()
                    for a in author_el.get_text(strip=True).split(",")
                    if a.strip()
                ]

            rating_el = item.select_one(".item-rate, em.item-rate")

            manga_id = self._url_to_id(href)

            results.append({
                "id": f"mn_{manga_id}",
                "source_id": manga_id,
                "title": title,
                "alt_titles": [],
                "cover_url": cover_url,
                "source": self.SOURCE_NAME,
                "language": "en",
                "status": "unknown",
                "type": "manga",
                "description": "",
                "authors": authors,
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
        if manga_id.startswith("mn_"):
            source_id = manga_id[3:]
        if source_id.startswith("manga-"):
            return f"https://chapmanganato.to/{source_id}"
        return f"https://chapmanganato.to/{source_id}"

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url, headers=self._referer_headers())
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one("h1, .story-info-right h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown"

        cover_el = soup.select_one(
            ".info-image img, .story-info-left img"
        )
        cover_url = cover_el.get("src", "") if cover_el else ""

        desc_el = soup.select_one(
            "#panel-story-info-description, .panel-story-info-description"
        )
        description = ""
        if desc_el:
            description = desc_el.get_text(strip=True)
            description = re.sub(r'^Description\s*:\s*', '', description)[:500]

        info_table = soup.select(
            ".variations-tableInfo tr, table.variations-tableInfo tr"
        )
        authors = []
        genres = []
        status = "unknown"
        alt_titles = []

        for row in info_table:
            label = row.select_one("td:first-child, .info-title")
            value = row.select_one("td:last-child, .info-value, td.table-value")
            if not label or not value:
                continue
            label_text = label.get_text(strip=True).lower()
            if "author" in label_text:
                for a in value.select("a"):
                    authors.append(a.get_text(strip=True))
            elif "genre" in label_text:
                for a in value.select("a"):
                    genres.append(a.get_text(strip=True))
            elif "status" in label_text:
                st = value.get_text(strip=True).lower()
                if "ongoing" in st:
                    status = "ongoing"
                elif "completed" in st:
                    status = "completed"
            elif "alternative" in label_text:
                alt_text = value.get_text(strip=True)
                alt_titles = [
                    a.strip() for a in alt_text.split(";") if a.strip()
                ]

        m_type = "manga"
        for g in genres:
            gl = g.lower()
            if "manhua" in gl:
                m_type = "manhua"
            elif "manhwa" in gl:
                m_type = "manhwa"

        reading_dir = "rtl" if m_type == "manga" else "vertical"

        chapters = self._parse_chapters_from_soup(soup, manga_id)

        source_id = manga_id
        if manga_id.startswith("mn_"):
            source_id = manga_id[3:]

        return {
            "id": f"mn_{source_id}",
            "source_id": source_id,
            "title": title,
            "alt_titles": alt_titles,
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
            "reading_direction": reading_dir,
            "chapters": chapters,
            "volumes": {},
            "related": [],
        }

    def get_chapters(
        self, manga_id: str, language: str = "en"
    ) -> List[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url, headers=self._referer_headers())
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_chapters_from_soup(soup, manga_id)

    def _parse_chapters_from_soup(self, soup, manga_id):
        chapters = []
        chapter_list = soup.select(
            ".row-content-chapter li a, "
            "ul.row-content-chapter li a, "
            ".chapter-list .row a"
        )

        if not chapter_list:
            chapter_list = soup.select("a[href*='chapter']")

        seen = set()
        for el in chapter_list:
            href = el.get("href", "")
            if not href or href in seen:
                continue

            text = el.get_text(strip=True)
            ch_match = re.search(r'[Cc]hapter\s*([\d.]+)', text)
            if not ch_match:
                ch_match = re.search(r'[Cc]h[.\s-]*([\d.]+)', href)
            if not ch_match:
                continue

            try:
                ch_num = float(ch_match.group(1))
            except ValueError:
                continue

            seen.add(href)
            ch_id = self.generate_id(self.SOURCE_NAME, manga_id, ch_num)
            chapters.append({
                "id": f"mn_{ch_id}",
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
        if chapter_id.startswith("mn_"):
            url = chapter_id[3:]

        if not url.startswith("http"):
            return []

        resp = self._get(url, headers=self._referer_headers(url))
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        images = []

        container = soup.select_one(
            ".container-chapter-reader, #chapter-content"
        )
        if container:
            for img in container.select("img"):
                src = img.get("src") or img.get("data-src")
                if src and src.startswith("http"):
                    images.append(src)

        if not images:
            for img in soup.select("img"):
                src = img.get("src", "")
                if any(
                    kw in src.lower()
                    for kw in ["/chapter/", "/manga/", "img.mghubcdn"]
                ):
                    images.append(src)

        return images

    def download_image(self, url: str, headers=None) -> Optional[bytes]:
        h = {"Referer": "https://chapmanganato.to/"}
        if headers:
            h.update(headers)
        return super().download_image(url, headers=h)

    def get_trending(self, language: str = "en", page: int = 1) -> List[Dict]:
        url = f"{self.BASE_URL}/genre-all/{page}"
        resp = self._get(url, headers=self._referer_headers())
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".content-genres-item"):
            link = item.select_one("a.genres-item-img")
            if not link:
                continue
            href = link.get("href", "")
            img = link.select_one("img")
            cover_url = img.get("src", "") if img else ""
            title_el = item.select_one("h3 a")
            title = title_el.get_text(strip=True) if title_el else ""
            manga_id = self._url_to_id(href)
            results.append({
                "id": f"mn_{manga_id}",
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