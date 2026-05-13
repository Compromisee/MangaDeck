"""
Threaded download engine.
Handles concurrent chapter/volume downloads with progress tracking,
bandwidth throttling, retry logic, and format conversion.
"""

import os
import time
import threading
import concurrent.futures
from typing import List, Dict, Optional, Callable
from pathlib import Path

from core.converter import Converter
from core.cropper import Cropper
from core.metadata import MetadataManager


class DownloadProgress:
    """Track progress for a single download task."""

    def __init__(self, task_id: str, title: str, total_items: int = 0):
        self._lock = threading.Lock()
        self.task_id = task_id
        self.title = title
        self.total_items = total_items
        self.completed_items = 0
        self.current_chapter = ""
        self.current_page = 0
        self.total_pages = 0
        self.status = "pending"  # pending, downloading, converting, complete, error, cancelled
        self.error_message = ""
        self.started_at = None
        self.completed_at = None
        self.bytes_downloaded = 0
        self.output_path = ""
        self.output_format = ""
        self.speed_bps = 0
        self._speed_samples = []

    def to_dict(self) -> Dict:
        with self._lock:
            elapsed = 0
            if self.started_at:
                end = self.completed_at or time.time()
                elapsed = end - self.started_at

            eta = 0
            if self.completed_items > 0 and self.total_items > 0 and elapsed > 0:
                rate = self.completed_items / elapsed
                remaining = self.total_items - self.completed_items
                eta = remaining / rate if rate > 0 else 0

            pct = 0
            if self.total_items > 0:
                pct = round(
                    (self.completed_items / self.total_items) * 100, 1
                )

            return {
                "task_id": self.task_id,
                "title": self.title,
                "status": self.status,
                "progress_percent": pct,
                "completed_items": self.completed_items,
                "total_items": self.total_items,
                "current_chapter": self.current_chapter,
                "current_page": self.current_page,
                "total_pages": self.total_pages,
                "bytes_downloaded": self.bytes_downloaded,
                "speed_bps": self.speed_bps,
                "elapsed_seconds": round(elapsed, 1),
                "eta_seconds": round(eta, 1),
                "error_message": self.error_message,
                "output_path": self.output_path,
                "output_format": self.output_format,
            }

    def update_speed(self, chunk_bytes: int):
        now = time.time()
        with self._lock:
            self._speed_samples.append((now, chunk_bytes))
            # Keep last 5 seconds of samples
            cutoff = now - 5
            self._speed_samples = [
                (t, b) for t, b in self._speed_samples if t > cutoff
            ]
            if len(self._speed_samples) > 1:
                duration = self._speed_samples[-1][0] - self._speed_samples[0][0]
                total_bytes = sum(b for _, b in self._speed_samples)
                if duration > 0:
                    self.speed_bps = int(total_bytes / duration)


class DownloadEngine:
    """
    Multi-threaded download engine with bandwidth control,
    progress tracking, and format conversion pipeline.
    """

    def __init__(self, config, logger, aggregator):
        self.config = config
        self.logger = logger
        self.aggregator = aggregator
        self.converter = Converter(config, logger)
        self.cropper = Cropper(config, logger)
        self.metadata = MetadataManager(config, logger)

        self._lock = threading.Lock()
        self._tasks = {}  # task_id -> DownloadProgress
        self._task_counter = 0
        self._active_downloads = 0
        self._cancelled = set()

        max_workers = config.get("max_concurrent_downloads", 4)
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        )
        self._image_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.get("max_concurrent_images", 8)
        )

        # Bandwidth throttling
        self._bandwidth_limit = config.get("bandwidth_limit_kbps", 0) * 1024
        self._bandwidth_lock = threading.Lock()
        self._bandwidth_used = 0
        self._bandwidth_reset_time = time.time()

    def _next_task_id(self) -> str:
        with self._lock:
            self._task_counter += 1
            return f"task_{self._task_counter:06d}"

    def get_all_tasks(self) -> List[Dict]:
        """Get status of all tasks."""
        with self._lock:
            tasks = list(self._tasks.values())
        return [t.to_dict() for t in tasks]

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task."""
        with self._lock:
            task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a download task."""
        with self._lock:
            if task_id in self._tasks:
                self._cancelled.add(task_id)
                self._tasks[task_id].status = "cancelled"
                return True
        return False

    def clear_completed(self):
        """Remove completed/error/cancelled tasks from list."""
        with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.status in ("complete", "error", "cancelled")
            ]
            for tid in to_remove:
                del self._tasks[tid]
                self._cancelled.discard(tid)

    def download(
        self,
        manga_id: str,
        chapter_range: List[float] = None,
        volume_range: List[float] = None,
        output_format: str = None,
        output_dir: str = None,
        language: str = None,
        title: str = None,
        source: str = None,
        source_ids: Dict = None,
        reading_direction: str = None,
        on_complete: Callable = None,
    ) -> str:
        """
        Start a download task. Returns task_id.
        """
        task_id = self._next_task_id()
        fmt = output_format or self.config.get("default_format", "cbz")
        lang = language or self.config.get("language", "en")
        out_dir = output_dir or self.config.get_output_dir()

        progress = DownloadProgress(task_id, title or manga_id, 0)
        progress.output_format = fmt
        progress.status = "pending"

        with self._lock:
            self._tasks[task_id] = progress

        self._executor.submit(
            self._download_task,
            task_id, manga_id, chapter_range, volume_range,
            fmt, out_dir, lang, title, source, source_ids,
            reading_direction, on_complete,
        )

        return task_id

    def download_chapters(
        self,
        chapters: List[Dict],
        title: str,
        output_format: str = None,
        output_dir: str = None,
        reading_direction: str = None,
        on_complete: Callable = None,
    ) -> str:
        """
        Download specific chapters directly. Returns task_id.
        """
        task_id = self._next_task_id()
        fmt = output_format or self.config.get("default_format", "cbz")
        out_dir = output_dir or self.config.get_output_dir()

        progress = DownloadProgress(task_id, title, len(chapters))
        progress.output_format = fmt
        progress.status = "pending"

        with self._lock:
            self._tasks[task_id] = progress

        self._executor.submit(
            self._download_chapters_task,
            task_id, chapters, title, fmt, out_dir,
            reading_direction, on_complete,
        )

        return task_id

    def _download_task(
        self, task_id, manga_id, chapter_range, volume_range,
        fmt, out_dir, language, title, source, source_ids,
        reading_direction, on_complete,
    ):
        """Main download task executed in thread."""
        progress = self._tasks[task_id]
        progress.status = "downloading"
        progress.started_at = time.time()

        try:
            # Get manga details if title not provided
            if not title:
                details = self.aggregator.get_manga_details(manga_id, source)
                if details:
                    title = details.get("title", manga_id)
                    if not reading_direction:
                        reading_direction = details.get("reading_direction", "rtl")
                    if not source_ids:
                        source_ids = {details["source"]: details["source_id"]}
                else:
                    title = manga_id

            progress.title = title
            self.logger.info(
                f"[Download] Starting: {title}", category="download"
            )

            # Get complete chapter list via aggregation
            chapters, source_map = self.aggregator.get_complete_chapters(
                manga_id, title=title, language=language,
                source_ids=source_ids,
            )

            if not chapters:
                raise Exception("No chapters found")

            # Filter by range
            if chapter_range:
                chapters = [
                    ch for ch in chapters
                    if ch["chapter_number"] in chapter_range
                ]

            if volume_range:
                chapters = [
                    ch for ch in chapters
                    if ch.get("volume_number") and ch["volume_number"] in volume_range
                ]

            if not chapters:
                raise Exception("No chapters match the specified range")

            progress.total_items = len(chapters)

            self.logger.info(
                f"[Download] {title}: {len(chapters)} chapters to download",
                category="download",
            )

            # Download each chapter
            self._download_chapters_task(
                task_id, chapters, title, fmt, out_dir,
                reading_direction, on_complete,
            )

        except Exception as e:
            progress.status = "error"
            progress.error_message = str(e)
            progress.completed_at = time.time()
            self.logger.error(
                f"[Download] Failed: {title} - {e}", category="download"
            )

    def _download_chapters_task(
        self, task_id, chapters, title, fmt, out_dir,
        reading_direction, on_complete,
    ):
        """Download and convert a list of chapters."""
        progress = self._tasks[task_id]
        if progress.status == "pending":
            progress.status = "downloading"
            progress.started_at = time.time()
        progress.total_items = len(chapters)

        safe_title = self._safe_filename(title)
        manga_dir = os.path.join(out_dir, safe_title)
        images_dir = os.path.join(manga_dir, "_images")
        os.makedirs(images_dir, exist_ok=True)

        chapter_images = {}  # chapter_number -> [image_paths]

        try:
            for i, chapter in enumerate(chapters):
                if task_id in self._cancelled:
                    progress.status = "cancelled"
                    return

                ch_num = chapter["chapter_number"]
                ch_str = (
                    str(int(ch_num)) if ch_num == int(ch_num)
                    else str(ch_num)
                )
                progress.current_chapter = f"Chapter {ch_str}"

                self.logger.debug(
                    f"[Download] {title} Ch.{ch_str} from {chapter['source']}",
                    category="download",
                )

                # Get image URLs
                ch_id = chapter.get("source_id", chapter["id"])
                source = chapter.get("source", "")

                # For scraped sources, source_id is the URL
                images = self.aggregator.get_chapter_images(ch_id, source)

                if not images:
                    # Try using the URL directly
                    url = chapter.get("url", "")
                    if url:
                        images = self.aggregator.get_chapter_images(url, source)

                if not images:
                    self.logger.warning(
                        f"[Download] No images for Ch.{ch_str}",
                        category="download",
                    )
                    progress.completed_items = i + 1
                    continue

                progress.total_pages = len(images)
                progress.current_page = 0

                # Download images concurrently
                ch_dir = os.path.join(
                    images_dir, f"chapter_{ch_str.zfill(5)}"
                )
                os.makedirs(ch_dir, exist_ok=True)

                page_paths = self._download_chapter_images(
                    task_id, images, ch_dir, source, progress
                )

                if page_paths:
                    # Auto-crop if enabled
                    if self.config.get("auto_crop", True):
                        page_paths = self.cropper.crop_images(page_paths)

                    chapter_images[ch_num] = page_paths

                progress.completed_items = i + 1

                # Small delay between chapters
                delay = self.config.get("queue_delay_seconds", 2)
                time.sleep(min(delay, 1))

            if task_id in self._cancelled:
                progress.status = "cancelled"
                return

            # Convert to output format
            if not chapter_images:
                raise Exception("No images downloaded successfully")

            progress.status = "converting"
            self.logger.info(
                f"[Download] Converting {title} to {fmt}",
                category="download",
            )

            rd = reading_direction or self.config.get("reading_direction", "auto")
            if rd == "auto":
                rd = "rtl"

            # Get cover
            cover_path = None
            first_ch = min(chapter_images.keys())
            if chapter_images[first_ch]:
                cover_path = chapter_images[first_ch][0]

            metadata_dict = {
                "title": title,
                "reading_direction": rd,
                "language": self.config.get("language", "en"),
                "cover_path": cover_path,
            }

            output_path = self.converter.convert(
                chapter_images=chapter_images,
                title=title,
                output_dir=manga_dir,
                output_format=fmt,
                metadata=metadata_dict,
            )

            progress.output_path = output_path
            progress.status = "complete"
            progress.completed_at = time.time()

            self.logger.info(
                f"[Download] Complete: {title} -> {output_path}",
                category="download",
            )

            if on_complete:
                try:
                    on_complete(task_id, progress.to_dict())
                except Exception:
                    pass

        except Exception as e:
            if task_id not in self._cancelled:
                progress.status = "error"
                progress.error_message = str(e)
                progress.completed_at = time.time()
                self.logger.error(
                    f"[Download] Error: {title} - {e}", category="download"
                )

    def _download_chapter_images(
        self, task_id, image_urls, output_dir, source, progress
    ) -> List[str]:
        """Download all images for a chapter concurrently."""
        paths = [None] * len(image_urls)
        futures = {}

        for idx, url in enumerate(image_urls):
            if task_id in self._cancelled:
                return []

            ext = self._get_image_ext(url)
            filename = f"page_{idx + 1:04d}{ext}"
            filepath = os.path.join(output_dir, filename)

            future = self._image_executor.submit(
                self._download_single_image,
                url, filepath, source, task_id,
            )
            futures[future] = idx

        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                result = future.result(timeout=120)
                if result:
                    paths[idx] = result
                    progress.current_page = sum(1 for p in paths if p)
            except Exception as e:
                self.logger.debug(
                    f"[Download] Image failed: {e}", category="download"
                )

        return [p for p in paths if p]

    def _download_single_image(
        self, url, filepath, source, task_id
    ) -> Optional[str]:
        """Download a single image with retry and bandwidth throttling."""
        if task_id in self._cancelled:
            return None

        max_retries = self.config.get("max_retries", 3)

        for attempt in range(max_retries):
            if task_id in self._cancelled:
                return None

            try:
                data = self.aggregator.download_image(url, source)
                if not data:
                    continue

                # Bandwidth throttling
                self._throttle_bandwidth(len(data))

                with open(filepath, "wb") as f:
                    f.write(data)

                # Verify it is a valid image
                if os.path.getsize(filepath) < 100:
                    os.remove(filepath)
                    continue

                # Update progress
                task = self._tasks.get(task_id)
                if task:
                    task.bytes_downloaded += len(data)
                    task.update_speed(len(data))

                return filepath

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue

        return None

    def _throttle_bandwidth(self, chunk_size: int):
        """Apply bandwidth throttling if configured."""
        if self._bandwidth_limit <= 0:
            return

        with self._bandwidth_lock:
            now = time.time()
            if now - self._bandwidth_reset_time >= 1.0:
                self._bandwidth_used = 0
                self._bandwidth_reset_time = now

            self._bandwidth_used += chunk_size
            if self._bandwidth_used >= self._bandwidth_limit:
                sleep_time = 1.0 - (now - self._bandwidth_reset_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self._bandwidth_used = 0
                self._bandwidth_reset_time = time.time()

    def _safe_filename(self, name: str) -> str:
        """Create a safe filename from a string."""
        import re
        safe = re.sub(r'[<>:"/\\|?*]', '', name)
        safe = safe.strip(". ")
        if not safe:
            safe = "manga"
        return safe[:200]

    def _get_image_ext(self, url: str) -> str:
        """Get image extension from URL."""
        url_lower = url.lower().split("?")[0]
        if url_lower.endswith(".png"):
            return ".png"
        elif url_lower.endswith(".webp"):
            return ".webp"
        elif url_lower.endswith(".gif"):
            return ".gif"
        return ".jpg"

    def get_active_count(self) -> int:
        """Get number of active downloads."""
        with self._lock:
            return sum(
                1 for t in self._tasks.values()
                if t.status in ("downloading", "converting")
            )

    def get_stats(self) -> Dict:
        """Get download engine statistics."""
        with self._lock:
            tasks = list(self._tasks.values())

        active = sum(1 for t in tasks if t.status == "downloading")
        converting = sum(1 for t in tasks if t.status == "converting")
        complete = sum(1 for t in tasks if t.status == "complete")
        errored = sum(1 for t in tasks if t.status == "error")
        pending = sum(1 for t in tasks if t.status == "pending")
        total_bytes = sum(t.bytes_downloaded for t in tasks)

        return {
            "active": active,
            "converting": converting,
            "complete": complete,
            "error": errored,
            "pending": pending,
            "total_tasks": len(tasks),
            "total_bytes_downloaded": total_bytes,
        }