"""
Multi-API Aggregation Engine.
Actively gap-fills from ALL sources when primary source is incomplete.
For long-running series like One Piece Colored, if MangaDex stops at ch.763
the engine continues from Manganato, MangaKakalot, etc. to reach ch.1076+.
"""

import concurrent.futures
import threading
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from api.mangadex import MangaDexAPI
from api.mangakatana import MangaKatanaAPI
from api.manganato import ManganatoAPI
from api.mangahere import MangaHereAPI
from api.mangakakalot import MangaKakalotAPI
from api.webtoon import WebtoonAPI
from api.manhuaplus import ManhuaPlusAPI


class Aggregator:

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._lock = threading.Lock()

        self.apis = {
            "mangadex":     MangaDexAPI(config, logger),
            "mangakatana":  MangaKatanaAPI(config, logger),
            "manganato":    ManganatoAPI(config, logger),
            "mangahere":    MangaHereAPI(config, logger),
            "mangakakalot": MangaKakalotAPI(config, logger),
            "webtoon":      WebtoonAPI(config, logger),
            "manhuaplus":   ManhuaPlusAPI(config, logger),
        }

        self.priority = [
            "mangadex", "manganato", "mangakakalot",
            "mangakatana", "mangahere", "manhuaplus", "webtoon",
        ]

        enabled = config.get("enabled_apis", None)
        if enabled:
            self.enabled_apis = [a for a in self.priority if a in enabled]
        else:
            self.enabled_apis = list(self.priority)

        max_w = config.get("max_api_workers", 4)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_w)
        self._availability_cache = {}

        # Cache: title -> {source_name: source_manga_id}
        self._title_source_cache = {}

    # ── Public ────────────────────────────────────────────────

    def get_enabled_apis(self) -> List[str]:
        return list(self.enabled_apis)

    def set_enabled_apis(self, apis: List[str]):
        self.enabled_apis = [a for a in self.priority if a in apis]
        self.config.set("enabled_apis", self.enabled_apis)

    def get_api(self, name: str):
        return self.apis.get(name)

    def check_availability(self) -> Dict[str, bool]:
        results = {}
        futures = {
            n: self._executor.submit(self.apis[n].is_available)
            for n in self.enabled_apis
        }
        for n, f in futures.items():
            try:
                results[n] = f.result(timeout=15)
            except Exception:
                results[n] = False
        with self._lock:
            self._availability_cache = results.copy()
        return results

    # ── Search ────────────────────────────────────────────────

    def search(
        self, query: str, language: str = "en",
        page: int = 1, sources: List[str] = None,
    ) -> List[Dict]:
        target = sources or self.enabled_apis
        all_results = []
        futures = {}
        for name in target:
            api = self.apis.get(name)
            if not api:
                continue
            futures[name] = self._executor.submit(
                self._safe_call, api.search, query, language, page
            )
        for name, f in futures.items():
            try:
                r = f.result(timeout=30)
                if r:
                    all_results.extend(r)
            except Exception as e:
                self.logger.warning(f"[Aggregator] Search {name}: {e}")

        merged = self._merge_results(all_results)

        # Cache source IDs for later aggregation
        for m in merged:
            title_lower = m.get("title", "").lower().strip()
            if title_lower and m.get("source_ids"):
                self._title_source_cache[title_lower] = m["source_ids"]

        return merged

    def get_trending(
        self, language: str = "en", page: int = 1,
        sources: List[str] = None,
    ) -> List[Dict]:
        target = sources or self.enabled_apis
        all_results = []
        futures = {}
        for name in target:
            api = self.apis.get(name)
            if not api:
                continue
            futures[name] = self._executor.submit(
                self._safe_call, api.get_trending, language, page
            )
        for name, f in futures.items():
            try:
                r = f.result(timeout=30)
                if r:
                    all_results.extend(r)
            except Exception:
                pass
        return self._merge_results(all_results)

    def _safe_call(self, fn, *args):
        try:
            return fn(*args) or []
        except Exception as e:
            self.logger.debug(f"[Aggregator] Call error: {e}")
            return []

    # ── Merge / deduplicate ───────────────────────────────────

    def _merge_results(self, results: List[Dict]) -> List[Dict]:
        if not results:
            return []

        merged = []
        used = set()

        for i, r in enumerate(results):
            if i in used:
                continue
            group = [r]
            src_names = [r.get("source", "")]

            for j in range(i + 1, len(results)):
                if j in used:
                    continue
                if self._title_sim(r.get("title", ""), results[j].get("title", "")) > 0.72:
                    group.append(results[j])
                    src_names.append(results[j].get("source", ""))
                    used.add(j)
            used.add(i)

            primary = max(group, key=lambda x: (
                len(x.get("description", ""))
                + len(x.get("genres", []))
                + (1 if x.get("cover_url") else 0)
                + (1 if x.get("chapter_count") else 0)
            ))

            if not primary.get("cover_url"):
                for g in group:
                    if g.get("cover_url"):
                        primary["cover_url"] = g["cover_url"]
                        break

            unique_src = sorted(set(s for s in src_names if s))
            src_ids = {}
            for g in group:
                src = g.get("source", "")
                sid = g.get("source_id", "")
                if src and sid:
                    src_ids[src] = sid

            merged.append({
                "id":               primary.get("id", ""),
                "source_id":        primary.get("source_id", ""),
                "title":            primary.get("title", ""),
                "alt_titles":       primary.get("alt_titles", []),
                "cover_url":        primary.get("cover_url", ""),
                "source":           primary.get("source", ""),
                "sources":          unique_src,
                "source_ids":       src_ids,
                "language":         primary.get("language", "en"),
                "status":           primary.get("status", "unknown"),
                "type":             primary.get("type", "manga"),
                "description":      primary.get("description", ""),
                "authors":          primary.get("authors", []),
                "genres":           primary.get("genres", []),
                "chapter_count":    primary.get("chapter_count"),
                "year":             primary.get("year"),
                "url":              primary.get("url", ""),
                "reading_direction": primary.get("reading_direction", "rtl"),
            })

        return merged

    def _title_sim(self, a: str, b: str) -> float:
        a, b = a.lower().strip(), b.lower().strip()
        if a == b:
            return 1.0
        return SequenceMatcher(None, a, b).ratio()

    # ── Details ───────────────────────────────────────────────

    def get_manga_details(
        self, manga_id: str, source: str = None
    ) -> Optional[Dict]:
        if source:
            api = self.apis.get(source)
            if api:
                return self._clean_details(api.get_manga_details(manga_id))
            return None

        api = self._api_from_id(manga_id)
        if api:
            return self._clean_details(api.get_manga_details(manga_id))

        for name in self.enabled_apis:
            try:
                r = self.apis[name].get_manga_details(manga_id)
                if r:
                    return self._clean_details(r)
            except Exception:
                continue
        return None

    def _clean_details(self, d: Optional[Dict]) -> Optional[Dict]:
        if not d:
            return None

        chapters = []
        for ch in d.get("chapters", []):
            chapters.append({
                "id":               ch.get("id", ""),
                "source_id":        ch.get("source_id", ""),
                "chapter_number":   ch.get("chapter_number", 0),
                "volume_number":    ch.get("volume_number"),
                "title":            ch.get("title", ""),
                "language":         ch.get("language", "en"),
                "pages":            ch.get("pages"),
                "source":           ch.get("source", ""),
                "url":              ch.get("url", ""),
                "date":             ch.get("date"),
                "scanlation_group": ch.get("scanlation_group"),
            })

        related = []
        for r in d.get("related", []):
            related.append({
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "relation": r.get("relation", "related"),
            })

        return {
            "id":               d.get("id", ""),
            "source_id":        d.get("source_id", ""),
            "title":            d.get("title", ""),
            "alt_titles":       d.get("alt_titles", []),
            "cover_url":        d.get("cover_url", ""),
            "source":           d.get("source", ""),
            "sources":          d.get("sources", [d.get("source", "")]),
            "source_ids":       d.get("source_ids", {}),
            "language":         d.get("language", "en"),
            "status":           d.get("status", "unknown"),
            "type":             d.get("type", "manga"),
            "description":      d.get("description", ""),
            "authors":          d.get("authors", []),
            "genres":           d.get("genres", []),
            "chapter_count":    len(chapters),
            "year":             d.get("year"),
            "url":              d.get("url", ""),
            "reading_direction": d.get("reading_direction", "rtl"),
            "chapters":         chapters,
            "volumes":          {},
            "related":          related,
        }

    # ── COMPLETE CHAPTER AGGREGATION ──────────────────────────
    # This is the core fix: aggressively search ALL sources
    # for chapters, not just the ones with known IDs.

    def get_complete_chapters(
        self,
        manga_id: str,
        title: str = "",
        language: str = "en",
        source_ids: Dict = None,
    ) -> Tuple[List[Dict], Dict[str, List]]:

        all_chapters: Dict[float, Dict] = {}
        source_map: Dict[str, List] = {}
        source_ids = dict(source_ids or {})

        # Merge cached source IDs if we have them
        if title:
            cached = self._title_source_cache.get(title.lower().strip(), {})
            for k, v in cached.items():
                if k not in source_ids:
                    source_ids[k] = v

        primary = self._source_from_id(manga_id)

        # 1) Gather chapters from all known source IDs in parallel
        self._gather_from_known_sources(
            manga_id, primary, source_ids, language, all_chapters, source_map
        )

        # 2) If we have a title, search EVERY enabled source for more chapters
        #    This is the key step for long series with partial coverage
        if title:
            self._search_all_sources_for_chapters(
                title, language, all_chapters, source_map, source_ids
            )

        # 3) Detect remaining gaps and try one more targeted fill
        if all_chapters:
            self._detect_and_fill_gaps(
                title, language, all_chapters, source_map
            )

        total = len(all_chapters)
        if total > 0:
            nums = sorted(all_chapters.keys())
            self.logger.info(
                f"[Aggregator] {title}: {total} chapters "
                f"(ch.{nums[0]}-{nums[-1]}) from "
                f"{', '.join(source_map.keys())}"
            )

        result = sorted(all_chapters.values(), key=lambda c: c["chapter_number"])
        return result, source_map

    def _gather_from_known_sources(
        self, manga_id, primary, source_ids, language,
        all_chapters, source_map,
    ):
        """Fetch chapters from all sources where we have a manga ID."""
        prefix_map = {
            "mangadex": "mdx_", "mangakatana": "mk_",
            "manganato": "mn_", "mangahere": "mh_",
            "mangakakalot": "mkk_", "webtoon": "wt_",
            "manhuaplus": "mhp_",
        }

        # Add primary source to source_ids if not present
        if primary and primary not in source_ids:
            raw_id = manga_id
            prefix = prefix_map.get(primary, "")
            if prefix and raw_id.startswith(prefix):
                raw_id = raw_id[len(prefix):]
            source_ids[primary] = raw_id

        futures = {}
        for src_name, src_id in source_ids.items():
            if src_name not in self.enabled_apis:
                continue
            api = self.apis.get(src_name)
            if not api:
                continue

            prefix = prefix_map.get(src_name, "")
            pid = src_id
            if prefix and not pid.startswith(prefix):
                pid = prefix + pid

            futures[src_name] = self._executor.submit(
                self._safe_call, api.get_chapters, pid, language
            )

        for src_name, f in futures.items():
            try:
                chapters = f.result(timeout=30) or []
                added = 0
                for ch in chapters:
                    num = ch.get("chapter_number")
                    if num is None:
                        continue
                    if num not in all_chapters:
                        all_chapters[num] = ch
                        source_map.setdefault(src_name, []).append(num)
                        added += 1
                if added:
                    self.logger.debug(
                        f"[Aggregator] {src_name}: added {added} chapters"
                    )
            except Exception as e:
                self.logger.debug(f"[Aggregator] {src_name} fetch failed: {e}")

    def _search_all_sources_for_chapters(
        self, title, language, all_chapters, source_map, known_source_ids,
    ):
        """
        For EVERY enabled source not yet used, search by title,
        find the best match, and grab its chapter list.
        This handles the case where source_ids are incomplete.
        """
        sources_with_chapters = set(source_map.keys())
        sources_to_search = [
            s for s in self.enabled_apis
            if s not in sources_with_chapters
        ]

        if not sources_to_search:
            return

        # Search all remaining sources for the title
        futures = {}
        for src_name in sources_to_search:
            api = self.apis.get(src_name)
            if not api:
                continue
            futures[src_name] = self._executor.submit(
                self._safe_call, api.search, title, language, 1
            )

        # For each source that found results, get chapters
        chapter_futures = {}
        for src_name, f in futures.items():
            try:
                results = f.result(timeout=20) or []
                if not results:
                    continue

                # Find best title match
                best = None
                best_sim = 0
                for r in results:
                    sim = self._title_sim(title, r.get("title", ""))
                    if sim > best_sim:
                        best_sim = sim
                        best = r

                if not best or best_sim < 0.55:
                    continue

                self.logger.debug(
                    f"[Aggregator] {src_name}: matched '{best.get('title')}' "
                    f"(sim={best_sim:.2f})"
                )

                api = self.apis[src_name]
                chapter_futures[src_name] = self._executor.submit(
                    self._safe_call, api.get_chapters, best["id"], language
                )

                # Cache this source ID for future use
                known_source_ids[src_name] = best.get("source_id", "")

            except Exception:
                continue

        for src_name, f in chapter_futures.items():
            try:
                chapters = f.result(timeout=30) or []
                added = 0
                for ch in chapters:
                    num = ch.get("chapter_number")
                    if num is None:
                        continue
                    if num not in all_chapters:
                        all_chapters[num] = ch
                        source_map.setdefault(src_name, []).append(num)
                        added += 1
                if added:
                    self.logger.info(
                        f"[Aggregator] {src_name}: filled {added} chapters via search"
                    )
            except Exception:
                continue

    def _detect_and_fill_gaps(
        self, title, language, all_chapters, source_map,
    ):
        """
        After initial gathering, check for integer gaps.
        Only try to fill if gap count is reasonable.
        """
        if not all_chapters or not title:
            return

        nums = sorted(all_chapters.keys())
        max_ch = int(max(nums))
        min_ch = int(min(nums))

        # Build set of integer chapters we have
        int_existing = set()
        for n in nums:
            if n == int(n):
                int_existing.add(int(n))

        expected = set(range(min_ch, max_ch + 1))
        gaps = expected - int_existing

        if not gaps:
            return

        # Only try filling if gaps are reasonable (< 50% of total)
        if len(gaps) > len(int_existing):
            self.logger.debug(
                f"[Aggregator] Too many gaps ({len(gaps)}) — likely intentional"
            )
            return

        self.logger.info(
            f"[Aggregator] {len(gaps)} gaps detected in ch.{min_ch}-{max_ch}"
        )

        # Try each source again specifically for gap chapters
        for src_name in self.enabled_apis:
            if not gaps:
                break
            if src_name in source_map:
                continue  # Already tried

            api = self.apis.get(src_name)
            if not api:
                continue

            try:
                results = api.search(title, language, 1) or []
                best = None
                best_sim = 0
                for r in results:
                    sim = self._title_sim(title, r.get("title", ""))
                    if sim > best_sim:
                        best_sim = sim
                        best = r

                if not best or best_sim < 0.5:
                    continue

                chapters = api.get_chapters(best["id"], language) or []
                for ch in chapters:
                    num = ch.get("chapter_number")
                    if num is None:
                        continue
                    if num not in all_chapters:
                        all_chapters[num] = ch
                        source_map.setdefault(src_name, []).append(num)
                        if num == int(num):
                            gaps.discard(int(num))
            except Exception:
                continue

    # ── Get volumes (aggregated) ──────────────────────────────

    def get_complete_volumes(
        self, manga_id: str, title: str = "",
        language: str = "en", source_ids: Dict = None,
    ) -> Dict[str, List[Dict]]:
        """
        Get chapters grouped by volume via full aggregation.
        Returns {"1": [ch_dicts], "2": [...], "none": [...]}
        """
        chapters, _ = self.get_complete_chapters(
            manga_id, title, language, source_ids
        )

        volumes = {}
        for ch in chapters:
            vol = ch.get("volume_number")
            if vol is not None:
                key = str(int(vol)) if vol == int(vol) else str(vol)
            else:
                key = "none"
            volumes.setdefault(key, []).append(ch)

        # Sort chapters within each volume
        for key in volumes:
            volumes[key].sort(key=lambda c: c.get("chapter_number", 0))

        return volumes

    # ── Chapter images / download ─────────────────────────────

    def get_chapter_images(
        self, chapter_id: str, source: str = None
    ) -> List[str]:
        if source:
            api = self.apis.get(source)
            if api:
                try:
                    return api.get_chapter_images(chapter_id) or []
                except Exception:
                    return []
            return []
        api = self._api_from_id(chapter_id)
        if api:
            try:
                return api.get_chapter_images(chapter_id) or []
            except Exception:
                return []
        return []

    def download_image(
        self, url: str, source: str = None
    ) -> Optional[bytes]:
        if source:
            api = self.apis.get(source)
            if api:
                return api.download_image(url)
        import requests as _req
        try:
            r = _req.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        return None

    # ── Utilities ─────────────────────────────────────────────

    PREFIX_MAP = {
        "mdx_": "mangadex", "mk_": "mangakatana",
        "mn_": "manganato", "mh_": "mangahere",
        "mkk_": "mangakakalot", "wt_": "webtoon",
        "mhp_": "manhuaplus",
    }

    def _api_from_id(self, manga_id: str):
        for prefix, name in self.PREFIX_MAP.items():
            if manga_id.startswith(prefix):
                return self.apis.get(name)
        return None

    def _source_from_id(self, manga_id: str) -> Optional[str]:
        for prefix, name in self.PREFIX_MAP.items():
            if manga_id.startswith(prefix):
                return name
        return None

    def get_supported_languages(self) -> List[str]:
        langs = set()
        for api in self.apis.values():
            langs.update(api.get_supported_languages())
        return sorted(langs)

    def get_api_info(self) -> List[Dict]:
        info = []
        for name in self.priority:
            api = self.apis.get(name)
            if not api:
                continue
            info.append({
                "name": name,
                "enabled": name in self.enabled_apis,
                "supports_manga": api.SUPPORTS_MANGA,
                "supports_manhwa": api.SUPPORTS_MANHWA,
                "supports_manhua": api.SUPPORTS_MANHUA,
                "rate_limit": api.RATE_LIMIT,
                "available": self._availability_cache.get(name),
            })
        return info