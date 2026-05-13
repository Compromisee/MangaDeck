"""
Configuration manager.
Handles loading, saving, and accessing all Mangadeck settings.
Supports JSON config file with defaults.
"""

import json
import os
import threading
from typing import Any, Dict, Optional
from pathlib import Path


DEFAULT_CONFIG = {
    # General
    "output_dir": os.path.join(os.path.expanduser("~"), "Mangadeck"),
    "default_format": "cbz",
    "language": "en",
    "reading_direction": "auto",
    "image_quality": "data",
    "max_concurrent_downloads": 4,
    "max_concurrent_images": 8,
    "max_api_workers": 4,
    "rate_limit_delay": None,
    "bandwidth_limit_kbps": 0,

    # APIs
    "enabled_apis": [
        "mangadex", "manganato", "mangakakalot",
        "mangakatana", "mangahere", "manhuaplus", "webtoon"
    ],
    "api_priority": [
        "mangadex", "manganato", "mangakakalot",
        "mangakatana", "mangahere", "manhuaplus", "webtoon"
    ],

    # Image processing
    "auto_crop": True,
    "crop_threshold": 10,
    "crop_min_ratio": 0.70,
    "crop_padding": 2,
    "max_image_width": 0,
    "max_image_height": 0,
    "convert_to_webp": False,
    "webp_quality": 85,
    "jpeg_quality": 92,

    # EPUB
    "epub_reading_direction": "auto",
    "epub_generate_cover": True,
    "epub_apple_books_compat": True,
    "epub_embed_fonts": False,
    "epub_page_width": 800,
    "epub_page_height": 1200,
    "epub_vertical_mode": False,

    # PDF
    "pdf_page_size": "auto",
    "pdf_margin": 0,
    "pdf_generate_cover": True,

    # CBZ
    "cbz_compression": 0,

    # Notifications
    "notify_on_complete": False,
    "notify_desktop": False,
    "discord_webhook_url": "",
    "telegram_bot_token": "",
    "telegram_chat_id": "",

    # Server
    "server_host": "127.0.0.1",
    "server_port": 5000,
    "theme": "dark",
    "high_contrast": False,
    "minimal_mode": False,

    # Logging
    "log_level": "INFO",
    "log_file": "",
    "log_max_entries": 5000,

    # Queue
    "auto_start_queue": False,
    "queue_delay_seconds": 2,
    "retry_failed": True,
    "max_retries": 3,
}


class Config:
    """Thread-safe configuration manager with file persistence."""

    def __init__(self, config_path: str = None):
        self._lock = threading.RLock()
        self._data = dict(DEFAULT_CONFIG)
        self._listeners = []

        if config_path:
            self._config_path = config_path
        else:
            config_dir = os.path.join(
                os.path.expanduser("~"), ".mangadeck"
            )
            os.makedirs(config_dir, exist_ok=True)
            self._config_path = os.path.join(config_dir, "config.json")

        self._load()

    def _load(self):
        """Load config from file, merging with defaults."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                with self._lock:
                    for key, value in saved.items():
                        self._data[key] = value
            except (json.JSONDecodeError, IOError) as e:
                pass

    def save(self):
        """Save current config to file."""
        with self._lock:
            data_copy = dict(self._data)
        try:
            os.makedirs(
                os.path.dirname(self._config_path), exist_ok=True
            )
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data_copy, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Set a config value and save."""
        with self._lock:
            old_value = self._data.get(key)
            self._data[key] = value
        self.save()
        self._notify_listeners(key, value, old_value)

    def get_all(self) -> Dict:
        """Get all config as dict."""
        with self._lock:
            return dict(self._data)

    def set_many(self, updates: Dict):
        """Set multiple values at once."""
        with self._lock:
            for key, value in updates.items():
                self._data[key] = value
        self.save()

    def reset(self, key: str = None):
        """Reset a key to default, or all keys if key is None."""
        with self._lock:
            if key:
                if key in DEFAULT_CONFIG:
                    self._data[key] = DEFAULT_CONFIG[key]
            else:
                self._data = dict(DEFAULT_CONFIG)
        self.save()

    def add_listener(self, callback):
        """Add a listener called on config changes: callback(key, new, old)."""
        self._listeners.append(callback)

    def _notify_listeners(self, key, new_value, old_value):
        if new_value != old_value:
            for cb in self._listeners:
                try:
                    cb(key, new_value, old_value)
                except Exception:
                    pass

    def get_output_dir(self) -> str:
        """Get output directory, creating it if needed."""
        d = self.get("output_dir", DEFAULT_CONFIG["output_dir"])
        os.makedirs(d, exist_ok=True)
        return d

    def get_config_path(self) -> str:
        return self._config_path

    def export_config(self) -> str:
        """Export config as JSON string."""
        with self._lock:
            return json.dumps(self._data, indent=2, ensure_ascii=False)

    def import_config(self, json_str: str) -> bool:
        """Import config from JSON string."""
        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                return False
            with self._lock:
                for key, value in data.items():
                    if key in DEFAULT_CONFIG:
                        self._data[key] = value
            self.save()
            return True
        except (json.JSONDecodeError, TypeError):
            return False