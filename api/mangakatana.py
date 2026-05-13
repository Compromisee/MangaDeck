"""
MangaKatana adapter.
Scrapes mangakatana.com for manga data.
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from api.base import BaseAPI


class MangaKatanaAPI(BaseAPI):
    SOURCE_NAME = "mangakatana"
    BASE_URL = "https://mangakatana.com"
    RATE_LIMIT = 1.0
    SUPPORTS_MANHUA = True
    SUPPORTS_MANHWA = True
    SUPPORTS_MANGA = True

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        params = {"search": query, "search_by": "book_name"}
        if page > 1:
            params["page"] = page

        resp = self._get(f"{self.BASE_URL}/", params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        book_list = soup.select("#book_list .item, .item")
        if not book_list:
            # Single result redirect
            title_el = soup.select_one("h1.heading")
            if title_el:
                parsed = self._parse_detail_page(soup, resp.url)
                if parsed:
                    results.append(parsed)
            return results

        for item in book_list:
            title_el = item.select_one(".title a, h3 a, .text a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if not url.startswith("http"):
                url = self.BASE_URL + url

            cover_el = item.select_one("img")
            cover_url = cover_el.get("src", "") if cover_el else ""

            genres = []
            genre_els = item.select(".genres a")
            for g in genre_els:
                genres.append(g.get_text(strip=True))

            status_el = item.select_one(".status")
            status = "unknown"
            if status_el:
                st = status_el.get_text(strip=True).lower()
                if "ongoing" in st:
                    status = "ongoing"
                elif "completed" in st or "complete" in st:
                    status = "completed"

            manga_id = self._url_to_id(url)

            results.append({
                "id": f"mk_{manga_id}",
                "source_id": manga_id,
                "title": title,
                "alt_titles": [],
                "cover_url": cover_url,
                "source": self.SOURCE_NAME,
                "language": "en",
                "status": status,
                "type": "manga",
                "description": "",
                "authors": [],
                "genres": genres,
                "chapter_count": None,
                "year": None,
                "url": url,
                "reading_direction": "rtl",
            })

        return results

    def _url_to_id(self, url):
        """Extract manga slug from URL."""
        parts = url.rstrip("/").split("/")
        for i, part in enumerate(parts):
            if part == "manga" and i + 1 < len(parts):
                return parts[i + 1]
        return parts[-1] if parts else ""

    def _id_to_url(self, manga_id):
        source_id = manga_id
        if manga_id.startswith("mk_"):
            source_id = manga_id[3:]
        return f"{self.BASE_URL}/manga/{source_id}"

    def _parse_detail_page(self, soup, url):
        title_el = soup.select_one("h1.heading")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        cover_el = soup.select_one(".cover img, .info img")
        cover_url = cover_el.get("src", "") if cover_el else ""

        desc_el = soup.select_one(".summary p, .summary")
        description = desc_el.get_text(strip=True)[:500] if desc_el else ""

        authors = []
        author_els = soup.select(".author a, a[href*='author']")
        for a in author_els:
            authors.append(a.get_text(strip=True))

        genres = []
        genre_els = soup.select(".genres a, .info .d-cell a[href*='genre']")
        for g in genre_els:
            genres.append(g.get_text(strip=True))

        status = "unknown"
        status_el = soup.select_one(".value.status, .status")
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

        reading_dir = "rtl"
        if m_type in ("manhwa", "manhua"):
            reading_dir = "vertical"

        manga_id = self._url_to_id(url)

        return {
            "id": f"mk_{manga_id}",
            "source_id": manga_id,
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
            "chapter_count": None,
            "year": None,
            "url": url if url.startswith("http") else self._id_to_url(manga_id),
            "reading_direction": reading_dir,
        }

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        result = self._parse_detail_page(soup, url)
        if not result:
            return None

        chapters = self._parse_chapters_from_soup(soup, manga_id)
        result["chapters"] = chapters
        result["chapter_count"] = len(chapters)
        result["volumes"] = self.get_volumes(manga_id)
        result["related"] = []
        return result

    def get_chapters(
        self, manga_id: str, language: str = "en"
    ) -> List[Dict]:
        url = self._id_to_url(manga_id)
        resp = self._get(url)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_chapters_from_soup(soup, manga_id)

    def _parse_chapters_from_soup(self, soup, manga_id):
        chapters = []
        chapter_rows = soup.select(
            ".chapters .chapter a, "
            "table.uk-table tr td a, "
            ".row.no-gutters a[href*='chapter']"
        )

        if not chapter_rows:
            chapter_rows = soup.select("a[href*='/chapter']")

        seen = set()
        for el in chapter_rows:
            url = el.get("href", "")
            if not url or url in seen:
                continue
            seen.add(url)

            text = el.get_text(strip=True)
            ch_match = re.search(r'[Cc]hapter\s*([\d.]+)', text)
            if not ch_match:
                ch_match = re.search(r'[Cc]h[.\s]*([\d.]+)', text)
            if not ch_match:
                ch_match = re.search(r'([\d.]+)', url.split("/")[-1])
            if not ch_match:
                continue

            try:
                ch_num = float(ch_match.group(1))
            except ValueError:
                continue

            if not url.startswith("http"):
                url = self.BASE_URL + url

            ch_id = self.generate_id(self.SOURCE_NAME, manga_id, ch_num)
            chapters.append({
                "id": f"mk_{ch_id}",
                "source_id": url,
                "chapter_number": ch_num,
                "volume_number": None,
                "title": text,
                "language": "en",
                "pages": None,
                "source": self.SOURCE_NAME,
                "url": url,
                "date": None,
                "scanlation_group": None,
            })

        chapters.sort(key=lambda c: c["chapter_number"])
        # Deduplicate
        unique = {}
        for ch in chapters:
            if ch["chapter_number"] not in unique:
                unique[ch["chapter_number"]] = ch
        return sorted(unique.values(), key=lambda c: c["chapter_number"])

    def get_chapter_images(self, chapter_id: str) -> List[str]:
        # chapter_id here is expected to be the URL or mk_ prefixed
        url = chapter_id
        if chapter_id.startswith("mk_"):
            # Need to look up the URL - this is the source_id stored
            url = chapter_id[3:]

        if not url.startswith("http"):
            return []

        resp = self._get(url)
        if not resp:
            return []

        images = []

        # Try JavaScript array extraction
        js_match = re.search(
            r'var\s+thzq\s*=\s*\[(.*?)\]', resp.text, re.DOTALL
        )
        if js_match:
            raw = js_match.group(1)
            urls = re.findall(r"'(https?://[^']+)'", raw)
            if urls:
                return urls
            urls = re.findall(r'"(https?://[^"]+)"', raw)
            if urls:
                return urls

        # Fallback: parse img tags
        soup = BeautifulSoup(resp.text, "html.parser")
        img_container = soup.select_one("#imgs, .chapter-content, #chapter-images")
        if img_container:
            for img in img_container.select("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if src and src.startswith("http"):
                    images.append(src)

        if not images:
            for img in soup.select("img"):
                src = img.get("src", "")
                if any(
                    kw in src.lower()
                    for kw in ["chapter", "manga", "page", "img", "pic"]
                ):
                    if src.startswith("http"):
                        images.append(src)

        return images

    def get_trending(self, language: str = "en", page: int = 1) -> List[Dict]:
        resp = self._get(f"{self.BASE_URL}/manga/page/{page}")
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select("#book_list .item, .item"):
            title_el = item.select_one(".title a, h3 a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if not url.startswith("http"):
                url = self.BASE_URL + url
            cover_el = item.select_one("img")
            cover_url = cover_el.get("src", "") if cover_el else ""
            manga_id = self._url_to_id(url)
            results.append({
                "id": f"mk_{manga_id}",
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
                "url": url,
                "reading_direction": "rtl",
            })
        return results