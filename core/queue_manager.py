"""
Queue and cart management system.
Handles download queue, cart for batch downloads, and scheduling.
"""

import threading
import time
import uuid
from typing import List, Dict, Optional, Callable
from collections import deque


class CartItem:
    """Single item in the download cart."""

    def __init__(
        self,
        manga_id: str,
        title: str,
        source: str,
        source_ids: Dict = None,
        cover_url: str = "",
        output_format: str = None,
        chapter_range: List[float] = None,
        volume_range: List[float] = None,
        language: str = "en",
        reading_direction: str = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.manga_id = manga_id
        self.title = title
        self.source = source
        self.source_ids = source_ids or {}
        self.cover_url = cover_url
        self.output_format = output_format
        self.chapter_range = chapter_range
        self.volume_range = volume_range
        self.language = language
        self.reading_direction = reading_direction
        self.added_at = time.time()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "manga_id": self.manga_id,
            "title": self.title,
            "source": self.source,
            "source_ids": self.source_ids,
            "cover_url": self.cover_url,
            "output_format": self.output_format,
            "chapter_range": self.chapter_range,
            "volume_range": self.volume_range,
            "language": self.language,
            "reading_direction": self.reading_direction,
            "added_at": self.added_at,
        }


class QueueItem:
    """Single item in the download queue."""

    def __init__(self, cart_item: CartItem, priority: int = 0):
        self.id = str(uuid.uuid4())[:8]
        self.cart_item = cart_item
        self.priority = priority
        self.status = "queued"  # queued, active, complete, error, cancelled
        self.task_id = None
        self.added_at = time.time()
        self.error_message = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "priority": self.priority,
            "status": self.status,
            "task_id": self.task_id,
            "error_message": self.error_message,
            "added_at": self.added_at,
            **self.cart_item.to_dict(),
        }


class QueueManager:
    """
    Manages the download cart and queue.
    Cart: items selected for batch download.
    Queue: ordered list of items being processed.
    """

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._lock = threading.RLock()

        self._cart = {}  # id -> CartItem
        self._queue = deque()  # QueueItem objects
        self._active = {}  # id -> QueueItem
        self._history = deque(maxlen=200)
        self._processing = False
        self._process_thread = None
        self._download_engine = None
        self._on_queue_complete = None
        self._stop_event = threading.Event()

    def set_download_engine(self, engine):
        """Set reference to download engine."""
        self._download_engine = engine

    def set_on_complete(self, callback: Callable):
        """Set callback for when entire queue completes."""
        self._on_queue_complete = callback

    # ---- Cart operations ----

    def add_to_cart(
        self,
        manga_id: str,
        title: str,
        source: str,
        source_ids: Dict = None,
        cover_url: str = "",
        output_format: str = None,
        chapter_range: List[float] = None,
        volume_range: List[float] = None,
        language: str = None,
        reading_direction: str = None,
    ) -> str:
        """Add an item to the cart. Returns item ID."""
        item = CartItem(
            manga_id=manga_id,
            title=title,
            source=source,
            source_ids=source_ids,
            cover_url=cover_url,
            output_format=output_format or self.config.get("default_format", "cbz"),
            chapter_range=chapter_range,
            volume_range=volume_range,
            language=language or self.config.get("language", "en"),
            reading_direction=reading_direction,
        )
        with self._lock:
            self._cart[item.id] = item

        self.logger.info(
            f"[Queue] Added to cart: {title}", category="queue"
        )
        return item.id

    def remove_from_cart(self, item_id: str) -> bool:
        """Remove an item from the cart."""
        with self._lock:
            if item_id in self._cart:
                del self._cart[item_id]
                return True
        return False

    def clear_cart(self):
        """Clear all cart items."""
        with self._lock:
            self._cart.clear()

    def get_cart(self) -> List[Dict]:
        """Get all cart items."""
        with self._lock:
            return [item.to_dict() for item in self._cart.values()]

    def get_cart_count(self) -> int:
        with self._lock:
            return len(self._cart)

    # ---- Queue operations ----

    def enqueue_cart(self) -> int:
        """Move all cart items to the queue. Returns count of items queued."""
        with self._lock:
            count = 0
            for item in self._cart.values():
                queue_item = QueueItem(item)
                self._queue.append(queue_item)
                count += 1
            self._cart.clear()

        self.logger.info(
            f"[Queue] Enqueued {count} items from cart", category="queue"
        )

        if self.config.get("auto_start_queue", False):
            self.start_processing()

        return count

    def enqueue_single(
        self,
        manga_id: str,
        title: str,
        source: str,
        source_ids: Dict = None,
        output_format: str = None,
        chapter_range: List[float] = None,
        volume_range: List[float] = None,
        language: str = None,
        reading_direction: str = None,
        priority: int = 0,
    ) -> str:
        """Add a single item directly to the queue. Returns queue item ID."""
        cart_item = CartItem(
            manga_id=manga_id,
            title=title,
            source=source,
            source_ids=source_ids,
            output_format=output_format or self.config.get("default_format", "cbz"),
            chapter_range=chapter_range,
            volume_range=volume_range,
            language=language or self.config.get("language", "en"),
            reading_direction=reading_direction,
        )
        queue_item = QueueItem(cart_item, priority)

        with self._lock:
            self._queue.append(queue_item)

        return queue_item.id

    def remove_from_queue(self, item_id: str) -> bool:
        """Remove an item from the queue."""
        with self._lock:
            self._queue = deque(
                q for q in self._queue if q.id != item_id
            )
            return True

    def clear_queue(self):
        """Clear all queued (non-active) items."""
        with self._lock:
            self._queue.clear()

    def get_queue(self) -> List[Dict]:
        """Get all queue items."""
        with self._lock:
            items = [q.to_dict() for q in self._queue]
            items.extend(q.to_dict() for q in self._active.values())
        return items

    def get_history(self) -> List[Dict]:
        """Get completed/failed queue history."""
        with self._lock:
            return [q.to_dict() for q in self._history]

    def get_queue_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def reorder_queue(self, item_id: str, new_position: int) -> bool:
        """Move a queue item to a new position."""
        with self._lock:
            item = None
            new_queue = deque()
            for q in self._queue:
                if q.id == item_id:
                    item = q
                else:
                    new_queue.append(q)

            if not item:
                return False

            items_list = list(new_queue)
            new_position = max(0, min(new_position, len(items_list)))
            items_list.insert(new_position, item)
            self._queue = deque(items_list)
            return True

    # ---- Processing ----

    def start_processing(self):
        """Start processing the queue."""
        if self._processing:
            return

        if not self._download_engine:
            self.logger.error("[Queue] No download engine set")
            return

        self._processing = True
        self._stop_event.clear()
        self._process_thread = threading.Thread(
            target=self._process_loop, daemon=True
        )
        self._process_thread.start()
        self.logger.info("[Queue] Processing started", category="queue")

    def stop_processing(self):
        """Stop processing after current item completes."""
        self._processing = False
        self._stop_event.set()
        self.logger.info("[Queue] Processing stopped", category="queue")

    def is_processing(self) -> bool:
        return self._processing

    def _process_loop(self):
        """Main queue processing loop."""
        while self._processing and not self._stop_event.is_set():
            with self._lock:
                if not self._queue:
                    self._processing = False
                    break

                queue_item = self._queue.popleft()
                self._active[queue_item.id] = queue_item

            queue_item.status = "active"
            cart = queue_item.cart_item

            try:
                task_id = self._download_engine.download(
                    manga_id=cart.manga_id,
                    chapter_range=cart.chapter_range,
                    volume_range=cart.volume_range,
                    output_format=cart.output_format,
                    language=cart.language,
                    title=cart.title,
                    source=cart.source,
                    source_ids=cart.source_ids,
                    reading_direction=cart.reading_direction,
                )
                queue_item.task_id = task_id

                # Wait for completion
                while True:
                    if self._stop_event.is_set():
                        break

                    task_status = self._download_engine.get_task(task_id)
                    if not task_status:
                        break

                    status = task_status.get("status", "")
                    if status in ("complete", "error", "cancelled"):
                        queue_item.status = status
                        if status == "error":
                            queue_item.error_message = task_status.get(
                                "error_message", ""
                            )
                        break

                    time.sleep(1)

            except Exception as e:
                queue_item.status = "error"
                queue_item.error_message = str(e)
                self.logger.error(
                    f"[Queue] Error processing {cart.title}: {e}",
                    category="queue",
                )

            with self._lock:
                del self._active[queue_item.id]
                self._history.appendleft(queue_item)

            # Delay between queue items
            delay = self.config.get("queue_delay_seconds", 2)
            time.sleep(delay)

        self._processing = False

        # Notify queue completion
        if self._on_queue_complete:
            try:
                self._on_queue_complete()
            except Exception:
                pass

        self.logger.info("[Queue] Queue processing finished", category="queue")

    def get_stats(self) -> Dict:
        """Get queue statistics."""
        with self._lock:
            return {
                "cart_count": len(self._cart),
                "queue_count": len(self._queue),
                "active_count": len(self._active),
                "history_count": len(self._history),
                "is_processing": self._processing,
                "completed": sum(
                    1 for h in self._history if h.status == "complete"
                ),
                "failed": sum(
                    1 for h in self._history if h.status == "error"
                ),
            }