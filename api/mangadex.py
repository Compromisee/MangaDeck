"""
MangaDex API adapter.
Uses the official MangaDex API v5.
"""

import time
from typing import List, Dict, Optional
from api.base import BaseAPI


class MangaDexAPI(BaseAPI):
    SOURCE_NAME = "mangadex"
    BASE_URL = "https://api.mangadex.org"
    RATE_LIMIT = 0.25
    SUPPORTS_MANHUA = True
    SUPPORTS_MANHWA = True
    SUPPORTS_MANGA = True

    COVER_BASE = "https://uploads.mangadex.org/covers"
    IMG_BASE = "https://uploads.mangadex.org"

    LANG_MAP = {
        "en": "en", "ja": "ja", "ko": "ko", "zh": "zh",
        "zh-hk": "zh-hk", "fr": "fr", "de": "de", "es": "es",
        "es-la": "es-la", "pt": "pt-br", "pt-br": "pt-br",
        "it": "it", "ru": "ru", "pl": "pl", "ar": "ar",
        "th": "th", "vi": "vi", "id": "id", "tr": "tr",
    }

    def _map_lang(self, lang):
        return self.LANG_MAP.get(lang, lang)

    def _parse_manga(self, data, relationships=None):
        attrs = data.get("attributes", {})
        title_dict = attrs.get("title", {})
        title = (
            title_dict.get("en")
            or title_dict.get("ja-ro")
            or title_dict.get("ja")
            or next(iter(title_dict.values()), "Unknown")
        )

        alt_titles = []
        for at in attrs.get("altTitles", []):
            for v in at.values():
                alt_titles.append(v)

        desc_dict = attrs.get("description", {})
        description = desc_dict.get("en", next(iter(desc_dict.values()), ""))

        authors = []
        cover_filename = None
        rels = relationships or data.get("relationships", [])
        for rel in rels:
            if rel["type"] == "author":
                name = rel.get("attributes", {}).get("name")
                if name:
                    authors.append(name)
            elif rel["type"] == "cover_art":
                cover_filename = rel.get("attributes", {}).get("fileName")

        cover_url = ""
        if cover_filename:
            cover_url = f"{self.COVER_BASE}/{data['id']}/{cover_filename}.256.jpg"

        manga_type = attrs.get("originalLanguage", "ja")
        type_map = {"ja": "manga", "ko": "manhwa", "zh": "manhua"}
        m_type = type_map.get(manga_type, "manga")

        status_map = {
            "ongoing": "ongoing",
            "completed": "completed",
            "hiatus": "hiatus",
            "cancelled": "cancelled",
        }

        tags = []
        for tag in attrs.get("tags", []):
            tag_name = tag.get("attributes", {}).get("name", {})
            n = tag_name.get("en", next(iter(tag_name.values()), ""))
            if n:
                tags.append(n)

        reading_dir = "rtl"
        if m_type in ("manhwa", "manhua"):
            reading_dir = "vertical"
        if "Long Strip" in tags:
            reading_dir = "vertical"

        return {
            "id": f"mdx_{data['id']}",
            "source_id": data["id"],
            "title": title,
            "alt_titles": alt_titles,
            "cover_url": cover_url,
            "source": self.SOURCE_NAME,
            "language": attrs.get("originalLanguage", "ja"),
            "status": status_map.get(attrs.get("status"), "unknown"),
            "type": m_type,
            "description": description[:500] if description else "",
            "authors": authors,
            "genres": tags,
            "chapter_count": None,
            "year": attrs.get("year"),
            "url": f"https://mangadex.org/title/{data['id']}",
            "reading_direction": reading_dir,
        }

    def search(self, query: str, language: str = "en", page: int = 1) -> List[Dict]:
        limit = 20
        offset = (page - 1) * limit
        params = {
            "title": query,
            "limit": limit,
            "offset": offset,
            "includes[]": ["cover_art", "author"],
            "order[relevance]": "desc",
            "contentRating[]": ["safe", "suggestive", "erotica"],
        }

        if language and language != "all":
            params["availableTranslatedLanguage[]"] = [self._map_lang(language)]

        data = self._get_json(f"{self.BASE_URL}/manga", params=params)
        if not data or "data" not in data:
            return []

        results = []
        for item in data["data"]:
            parsed = self._parse_manga(item)
            results.append(parsed)
        return results

    def get_manga_details(self, manga_id: str) -> Optional[Dict]:
        source_id = manga_id
        if manga_id.startswith("mdx_"):
            source_id = manga_id[4:]

        params = {"includes[]": ["cover_art", "author", "artist"]}
        data = self._get_json(f"{self.BASE_URL}/manga/{source_id}", params=params)
        if not data or "data" not in data:
            return None

        result = self._parse_manga(data["data"])

        chapters = self.get_chapters(manga_id)
        result["chapters"] = chapters
        result["chapter_count"] = len(chapters)
        result["volumes"] = self.get_volumes(manga_id)

        # Related manga
        related = []
        for rel in data["data"].get("relationships", []):
            if rel["type"] == "manga":
                r_attrs = rel.get("attributes", {})
                if r_attrs:
                    r_title = r_attrs.get("title", {})
                    related.append({
                        "id": f"mdx_{rel['id']}",
                        "title": r_title.get("en", next(iter(r_title.values()), "")),
                        "relation": rel.get("related", "related"),
                    })
        result["related"] = related

        return result

    def get_chapters(
        self, manga_id: str, language: str = "en"
    ) -> List[Dict]:
        source_id = manga_id
        if manga_id.startswith("mdx_"):
            source_id = manga_id[4:]

        all_chapters = []
        offset = 0
        limit = 100
        lang = self._map_lang(language)

        while True:
            params = {
                "manga": source_id,
                "limit": limit,
                "offset": offset,
                "translatedLanguage[]": [lang],
                "order[chapter]": "asc",
                "includes[]": ["scanlation_group"],
            }

            data = self._get_json(f"{self.BASE_URL}/chapter", params=params)
            if not data or "data" not in data:
                break

            for ch in data["data"]:
                attrs = ch.get("attributes", {})
                ch_num = attrs.get("chapter")
                if ch_num is None:
                    continue

                try:
                    ch_num = float(ch_num)
                except (ValueError, TypeError):
                    continue

                vol_num = attrs.get("volume")
                if vol_num:
                    try:
                        vol_num = float(vol_num)
                    except (ValueError, TypeError):
                        vol_num = None

                group = ""
                for rel in ch.get("relationships", []):
                    if rel["type"] == "scanlation_group":
                        group = rel.get("attributes", {}).get("name", "")
                        break

                all_chapters.append({
                    "id": f"mdx_{ch['id']}",
                    "source_id": ch["id"],
                    "chapter_number": ch_num,
                    "volume_number": vol_num,
                    "title": attrs.get("title", ""),
                    "language": attrs.get("translatedLanguage", lang),
                    "pages": attrs.get("pages"),
                    "source": self.SOURCE_NAME,
                    "url": f"https://mangadex.org/chapter/{ch['id']}",
                    "date": attrs.get("publishAt", ""),
                    "scanlation_group": group,
                })

            total = data.get("total", 0)
            offset += limit
            if offset >= total:
                break

        # Deduplicate by chapter number, keep first
        seen = {}
        unique = []
        for ch in all_chapters:
            num = ch["chapter_number"]
            if num not in seen:
                seen[num] = True
                unique.append(ch)

        unique.sort(key=lambda c: c["chapter_number"])
        return unique

    def get_chapter_images(self, chapter_id: str) -> List[str]:
        source_id = chapter_id
        if chapter_id.startswith("mdx_"):
            source_id = chapter_id[4:]

        data = self._get_json(f"{self.BASE_URL}/at-home/server/{source_id}")
        if not data:
            return []

        base_url = data.get("baseUrl", "")
        chapter_data = data.get("chapter", {})
        ch_hash = chapter_data.get("hash", "")
        pages = chapter_data.get("data", [])

        quality = self.config.get("image_quality", "data")
        if quality == "datasaver":
            pages = chapter_data.get("dataSaver", pages)
            return [f"{base_url}/data-saver/{ch_hash}/{p}" for p in pages]

        return [f"{base_url}/data/{ch_hash}/{p}" for p in pages]

    def get_trending(self, language: str = "en", page: int = 1) -> List[Dict]:
        limit = 20
        offset = (page - 1) * limit
        params = {
            "limit": limit,
            "offset": offset,
            "includes[]": ["cover_art", "author"],
            "order[followedCount]": "desc",
            "contentRating[]": ["safe", "suggestive"],
            "hasAvailableChapters": "true",
        }
        if language and language != "all":
            params["availableTranslatedLanguage[]"] = [self._map_lang(language)]

        data = self._get_json(f"{self.BASE_URL}/manga", params=params)
        if not data or "data" not in data:
            return []

        return [self._parse_manga(item) for item in data["data"]]

    def get_supported_languages(self) -> List[str]:
        return list(self.LANG_MAP.keys())