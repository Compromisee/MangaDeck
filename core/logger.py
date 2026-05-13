"""
Advanced logging system.
Supports file logging, in-memory log buffer for dashboard,
filtering, and log level management.
"""

import logging
import os
import time
import threading
from datetime import datetime
from typing import List, Dict, Optional
from collections import deque


class LogEntry:
    """Single log entry."""

    __slots__ = ("timestamp", "level", "message", "source", "category")

    def __init__(self, level: str, message: str, source: str = "", category: str = "general"):
        self.timestamp = datetime.now().isoformat()
        self.level = level
        self.message = message
        self.source = source
        self.category = category

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "category": self.category,
        }


class Logger:
    """
    Application logger with in-memory buffer for dashboard display,
    optional file logging, and filtering support.
    """

    LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()
        self._max_entries = config.get("log_max_entries", 5000)
        self._buffer = deque(maxlen=self._max_entries)
        self._level = self.LEVELS.get(
            config.get("log_level", "INFO").upper(), 20
        )

        # Python logging
        self._logger = logging.getLogger("mangadeck")
        self._logger.setLevel(logging.DEBUG)

        # Console handler
        console = logging.StreamHandler()
        console.setLevel(self._level)
        fmt = logging.Formatter(
            "  %(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )
        console.setFormatter(fmt)
        self._logger.addHandler(console)

        # File handler
        log_file = config.get("log_file", "")
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                fh = logging.FileHandler(log_file, encoding="utf-8")
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(logging.Formatter(
                    "%(asctime)s  %(levelname)-8s  %(message)s"
                ))
                self._logger.addHandler(fh)
            except (IOError, OSError):
                pass

        # Stats
        self._stats = {
            "debug": 0,
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
        }

    def _log(self, level: str, message: str, source: str = "", category: str = "general"):
        level_num = self.LEVELS.get(level.upper(), 20)
        if level_num < self._level:
            return

        entry = LogEntry(level.upper(), message, source, category)
        with self._lock:
            self._buffer.append(entry)
            self._stats[level.lower()] = self._stats.get(level.lower(), 0) + 1

        getattr(self._logger, level.lower(), self._logger.info)(message)

    def debug(self, message: str, source: str = "", category: str = "general"):
        self._log("DEBUG", message, source, category)

    def info(self, message: str, source: str = "", category: str = "general"):
        self._log("INFO", message, source, category)

    def warning(self, message: str, source: str = "", category: str = "general"):
        self._log("WARNING", message, source, category)

    def error(self, message: str, source: str = "", category: str = "general"):
        self._log("ERROR", message, source, category)

    def critical(self, message: str, source: str = "", category: str = "general"):
        self._log("CRITICAL", message, source, category)

    def get_logs(
        self,
        level: str = None,
        category: str = None,
        source: str = None,
        limit: int = 100,
        offset: int = 0,
        search: str = None,
    ) -> List[Dict]:
        """Get filtered log entries."""
        with self._lock:
            entries = list(self._buffer)

        if level:
            level_upper = level.upper()
            entries = [e for e in entries if e.level == level_upper]

        if category:
            entries = [e for e in entries if e.category == category]

        if source:
            entries = [e for e in entries if source.lower() in e.source.lower()]

        if search:
            search_lower = search.lower()
            entries = [
                e for e in entries
                if search_lower in e.message.lower()
            ]

        # Reverse for newest first
        entries.reverse()
        total = len(entries)
        entries = entries[offset:offset + limit]

        return {
            "entries": [e.to_dict() for e in entries],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def get_stats(self) -> Dict:
        """Get log statistics."""
        with self._lock:
            return {
                "total": len(self._buffer),
                "counts": dict(self._stats),
                "max_entries": self._max_entries,
            }

    def clear(self):
        """Clear log buffer."""
        with self._lock:
            self._buffer.clear()
            self._stats = {k: 0 for k in self._stats}

    def set_level(self, level: str):
        """Set log level."""
        level_num = self.LEVELS.get(level.upper(), 20)
        self._level = level_num
        for handler in self._logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.setLevel(level_num)