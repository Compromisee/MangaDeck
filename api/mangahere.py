"""
MangaHere adapter.
Scrapes mangahere.cc / fanfox.net
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from api.base import BaseAPI


class MangaHereAPI(BaseAPI):
    SOURCE_NAME = "mangahere"
    BASE_URL = "https://www.mangahere.cc"
    RATE_LIMIT = 1.5
    SUPPORTS_MANHUA = True
    SUPPORTS_MANHWA = True

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        params = {
            "title": query,
            "page": page,
        }
        resp = self._get(
            f"{self.BASE_URL}/search", params=params,
            headers={"Referer": self.BASE_URL}
        )
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        items = soup.select(
            ".manga-list-4-list > li, .line-list li"
        )
        for item in items:
            link = item.select_one("a")
            if not link:
                continue

            href = link.get("href", "")
            if not href.startswith("http"):
                href = self.BASE_URL + href

            title_el = item.select_one("p.manga-list-4-item-title a, a.manga-list-4-item-title")
            if not title_el:
                title_el = link
            title = title_el.get("title", "") or title_el.get_text(strip=True)

            img = item.select_one("img")
            cover_url = ""
            if img:
                cover_url = img.get("src") or img.get("data-src") or ""
                if cover_url.startswith("//"):
                    cover_url = "https:" + cover_url

            manga_id = self._url_to_id(href)

            results.append({
                "id": f"mh_{manga_id}",
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
        match = re.search(r'/manga/([^/]+)', url)
        return match.group(1) if match else url.rstrip("/").split("/")[-1]

    def _id_to_url(self, manga_id):
        source_id = manga_id
        if manga_id.startswith("mh_"):
            source_id = manga_id[3:]
        return f"{self.BASE_URL}/manga/{source_id}/"

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one(
            ".detail-info-right-title-font, h1, h2.title"
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown"

        cover_el = soup.select_one(".detail-info-cover-img img, .cover img")
        cover_url = ""
        if cover_el:
            cover_url = cover_el.get("src") or cover_el.get("data-src") or ""
            if cover_url.startswith("//"):
                cover_url = "https:" + cover_url

        desc_el = soup.select_one(
            ".fullcontent, .detail-info-right-content, p.detail-info-right-content"
        )
        description = desc_el.get_text(strip=True)[:500] if desc_el else ""

        authors = []
        for a in soup.select("a[href*='/author/'], .detail-info-right-say a"):
            authors.append(a.get_text(strip=True))

        genres = []
        for a in soup.select(
            ".detail-info-right-tag-list a, a[href*='/category/']"
        ):
            genres.append(a.get_text(strip=True))

        status = "unknown"
        status_el = soup.select_one(
            ".detail-info-right-title-tip, span.detail-info-right-title-tip"
        )
        if status_el:
            st = status_el.get_text(strip=True).lower()
            if "ongoing" in st:
                status = "ongoing"
            elif "completed" in st:
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
        if manga_id.startswith("mh_"):
            source_id = manga_id[3:]

        return {
            "id": f"mh_{source_id}",
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
            "ul.detail-main-list li a, "
            ".detail-main-list a, "
            "a[href*='/manga/'][href*='/c']"
        )

        for el in links:
            href = el.get("href", "")
            if not href or href in seen:
                continue

            ch_match = re.search(r'/c([\d.]+)', href)
            if not ch_match:
                continue

            try:
                ch_num = float(ch_match.group(1))
            except ValueError:
                continue

            seen.add(href)
            full_url = href
            if not full_url.startswith("http"):
                full_url = self.BASE_URL + href

            vol_match = re.search(r'/v(\d+)/', href)
            vol_num = float(vol_match.group(1)) if vol_match else None

            text = el.get_text(strip=True)
            ch_id = self.generate_id(self.SOURCE_NAME, manga_id, ch_num)

            chapters.append({
                "id": f"mh_{ch_id}",
                "source_id": full_url,
                "chapter_number": ch_num,
                "volume_number": vol_num,
                "title": text,
                "language": "en",
                "pages": None,
                "source": self.SOURCE_NAME,
                "url": full_url,
                "date": None,
                "scanlation_group": None,
            })

        chapters.sort(key=lambda c: c["chapter_number"])
        return chapters

    def get_chapter_images(self, chapter_id: str) -> List[str]:
        url = chapter_id
        if chapter_id.startswith("mh_"):
            url = chapter_id[3:]

        if not url.startswith("http"):
            return []

        resp = self._get(url, headers={"Referer": self.BASE_URL})
        if not resp:
            return []

        images = []

        # MangaHere uses JavaScript to load images
        # Try to extract from script tags
        page_count_match = re.search(
            r'imagecount\s*=\s*(\d+)', resp.text
        )
        chapterid_match = re.search(
            r'chapterid\s*=\s*(\d+)', resp.text
        )

        # Extract directly visible images
        soup = BeautifulSoup(resp.text, "html.parser")
        for img in soup.select("#viewer img, .reader-main-img"):
            src = img.get("src") or img.get("data-original")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                images.append(src)

        # Try script extraction
        if not images:
            src_matches = re.findall(
                r"'(https?://[^']*\.(?:jpg|png|webp)[^']*)'", resp.text
            )
            images.extend(src_matches)

        return images

    def download_image(self, url: str, headers=None) -> Optional[bytes]:
        h = {"Referer": self.BASE_URL + "/"}
        if headers:
            h.update(headers)
        return super().download_image(url, headers=h)