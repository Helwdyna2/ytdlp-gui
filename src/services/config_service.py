"""Configuration management service."""

import json
import logging
import os
import sys
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.platform_utils import (
    get_config_path,
    get_default_output_dir,
    ensure_dirs,
    get_data_dir,
)
from ..utils.constants import (
    DEFAULT_CONCURRENT_LIMIT,
    DEFAULT_FORCE_OVERWRITE,
    DEFAULT_VIDEO_ONLY,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_SPLITTER_SIZES,
    AUTO_SAVE_INTERVAL_MS,
    DEBOUNCE_PARSE_MS,
    LOG_MAX_LINES,
)

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "version": 1,
    "window": {
        "width": DEFAULT_WINDOW_WIDTH,
        "height": DEFAULT_WINDOW_HEIGHT,
        "x": None,
        "y": None,
        "splitter_sizes": DEFAULT_SPLITTER_SIZES,
        "maximized": False,
    },
    "dialogs": {
        "last_dir": "",  # Global last directory for file dialogs
    },
    "download": {
        "output_dir": "",
        "concurrent_limit": DEFAULT_CONCURRENT_LIMIT,
        "force_overwrite": DEFAULT_FORCE_OVERWRITE,
        "video_only": DEFAULT_VIDEO_ONLY,
        "cookies_path": "",
        "filename_templates": {},  # Map of domain -> template
        "default_template": "%(title)s",  # Fallback template
    },
    "behavior": {
        "auto_save_interval_ms": AUTO_SAVE_INTERVAL_MS,
        "debounce_parse_ms": DEBOUNCE_PARSE_MS,
        "log_max_lines": LOG_MAX_LINES,
        "confirm_on_exit": True,
        "clear_completed_delay_ms": 2000,
        "download_log_auto_scroll": True,  # Auto-scroll download log
    },
    "convert": {
        "output_dir": "",
        "codec": "libx264",
        "crf": 23,
        "preset": "medium",
        "use_hardware_accel": False,
    },
    "trim": {
        "mode": "single",  # "single" or "batch"
        "single_lossless": True,
        "single_output_dir": "",
        "batch_lossless": True,
        "batch_output_dir": "",
        "global_start_offset": 0.0,
        "global_end_offset": 0.0,
    },
    "rename": {
        "last_folder": "",
        "find_text": "",
        "replace_text": "",
        "case_sensitive": False,
        "use_regex": False,
    },
    "sort": {
        "last_source_folder": "",
        "last_dest_folder": "",
        "use_copy": False,  # False = move, True = copy
        "preserve_subfolders": True,
        "criteria_order": ["fps", "resolution", "orientation", "codec", "bitrate"],
        "criteria_enabled": {
            "fps": True,
            "resolution": True,
            "orientation": True,
            "codec": False,
            "bitrate": False,
        },
    },
    "match": {
        "last_folder": "",
        "search_porndb": True,
        "search_stashdb": True,
        "porndb_first": True,
        "preserve_tags": True,
        "include_already_named": False,
        "custom_studios": [],
        "skip_keywords": [],
        "cookies_dir": "",
    },
    "extract_urls": {
        "output_dir": "",
        "auto_scroll_enabled": True,
        "max_scrolls": 200,
        "idle_limit": 5,
        "delay_ms": 800,
        "max_bounce_attempts": 3,
    },
    "auth": {
        "profile_dir": "",
        "cookies_file_path": "",
        "last_login_url": "",
    },
    "playwright": {
        "browser": "chromium",
    },
    "ffmpeg": {
        "warning_dismissed": False,
    },
    "download_polite": {
        "sleep_requests_seconds": 0.0,
        "min_sleep_interval_seconds": 0.0,
        "max_sleep_interval_seconds": 0.0,
        "limit_rate": "",
        "retries": 10,
        "retry_sleep_http": {
            "mode": "off",
            "start": 0.0,
            "end": 0.0,
            "step": 1.0,
            "base": 2.0,
        },
        "retry_sleep_fragment_enabled": False,
        "retry_sleep_fragment": {
            "mode": "off",
            "start": 0.0,
            "end": 0.0,
            "step": 1.0,
            "base": 2.0,
        },
    },
}


class ConfigService:
    """
    Configuration management with JSON persistence.

    Features:
    - Automatic migration for config changes
    - Validation of values
    - Default fallbacks
    - Dot-notation access
    """

    CONFIG_VERSION = 1
    DEFAULT_SAVE_DELAY_MS = 150

    _instance: Optional["ConfigService"] = None

    def __new__(cls, config_path: Optional[str] = None):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration service."""
        if self._initialized:
            return

        if config_path:
            self.config_path = Path(config_path)
        else:
            ensure_dirs()
            self.config_path = get_config_path()

        self._config: Dict[str, Any] = {}
        self._config_lock = threading.RLock()
        self._save_timer: Optional[threading.Timer] = None
        self._load()
        self._initialized = True

    def _load(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    self._config = self._merge_with_defaults(loaded)
                    # Check for migration
                    self._migrate_if_needed(loaded)
                    self._apply_dynamic_defaults()
            else:
                self._config = deepcopy(DEFAULT_CONFIG)
                # Set default output dir
                self._config["download"]["output_dir"] = str(get_default_output_dir())
                self._apply_dynamic_defaults()
                self.save()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = deepcopy(DEFAULT_CONFIG)
            self._config["download"]["output_dir"] = str(get_default_output_dir())
            self._apply_dynamic_defaults()

    def _merge_with_defaults(self, loaded: dict) -> dict:
        """Deep merge loaded config with defaults."""
        result = deepcopy(DEFAULT_CONFIG)
        self._deep_update(result, loaded)
        return result

    def _deep_update(self, base: dict, update: dict):
        """Recursively update base dict with update dict."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def _migrate_if_needed(self, loaded: dict):
        """Migrate old config versions."""
        version = loaded.get("version", 0)
        if version < self.CONFIG_VERSION:
            logger.info(
                f"Migrating config from version {version} to {self.CONFIG_VERSION}"
            )

            # No migrations yet (version 1 is current)

            self._config["version"] = self.CONFIG_VERSION
            self.save()

    def _apply_dynamic_defaults(self) -> None:
        """Apply dynamic defaults for paths."""
        changed = False

        if not self._config.get("download", {}).get("output_dir"):
            self._config["download"]["output_dir"] = str(get_default_output_dir())
            changed = True

        extract = self._config.get("extract_urls", {})
        if not extract.get("output_dir"):
            extract["output_dir"] = str(get_data_dir() / "extracted_urls")
            changed = True

        self._config["extract_urls"] = extract

        auth = self._config.get("auth", {})
        if not auth.get("profile_dir"):
            auth["profile_dir"] = str(get_data_dir() / "browser_profiles" / "global")
            changed = True
        if not auth.get("cookies_file_path"):
            auth["cookies_file_path"] = str(
                get_data_dir() / "cookies" / "playwright_cookies.txt"
            )
            changed = True
        if "last_login_url" not in auth:
            auth["last_login_url"] = ""
            changed = True

        self._config["auth"] = auth

        playwright = self._config.get("playwright", {})
        if not playwright.get("browser"):
            playwright["browser"] = "chromium"
            changed = True
        self._config["playwright"] = playwright

        polite = self._config.get("download_polite", {})
        polite_changed = False
        if "sleep_requests_seconds" not in polite:
            polite["sleep_requests_seconds"] = 0.0
            polite_changed = True
        if "min_sleep_interval_seconds" not in polite:
            polite["min_sleep_interval_seconds"] = 0.0
            polite_changed = True
        if "max_sleep_interval_seconds" not in polite:
            polite["max_sleep_interval_seconds"] = 0.0
            polite_changed = True
        if "limit_rate" not in polite:
            polite["limit_rate"] = ""
            polite_changed = True
        if "retries" not in polite:
            polite["retries"] = 10
            polite_changed = True
        if "retry_sleep_http" not in polite:
            polite["retry_sleep_http"] = {
                "mode": "off",
                "start": 0.0,
                "end": 0.0,
                "step": 1.0,
                "base": 2.0,
            }
            polite_changed = True
        if "retry_sleep_fragment_enabled" not in polite:
            polite["retry_sleep_fragment_enabled"] = False
            polite_changed = True
        if "retry_sleep_fragment" not in polite:
            polite["retry_sleep_fragment"] = {
                "mode": "off",
                "start": 0.0,
                "end": 0.0,
                "step": 1.0,
                "base": 2.0,
            }
            polite_changed = True
        self._config["download_polite"] = polite
        if polite_changed:
            changed = True

        if changed:
            self.save()

    def _cancel_queued_save_locked(self) -> None:
        """Cancel any pending delayed save while holding the config lock."""
        if self._save_timer is None:
            return
        self._save_timer.cancel()
        self._save_timer = None

    def queue_save(self, delay_ms: Optional[int] = None) -> None:
        """Queue a debounced save for bursty UI updates."""
        delay_seconds = (
            (delay_ms if delay_ms is not None else self.DEFAULT_SAVE_DELAY_MS) / 1000.0
        )

        with self._config_lock:
            self._cancel_queued_save_locked()
            self._save_timer = threading.Timer(delay_seconds, self._run_queued_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _run_queued_save(self) -> None:
        """Flush a queued save request."""
        with self._config_lock:
            self._save_timer = None

        self.save()

    def save(self):
        """Save configuration to file atomically.

        Uses temp file + fsync + rename pattern for atomicity.
        Handles Windows-specific atomic replace requirements.
        Cleans up temp file on any failure.
        """
        temp_fd = None
        temp_path = None

        try:
            with self._config_lock:
                self._cancel_queued_save_locked()
                config_to_save = deepcopy(self._config)

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            config_to_save["version"] = self.CONFIG_VERSION

            # Create temp file in same directory for atomic rename
            config_dir = os.path.dirname(self.config_path)
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.tmp',
                prefix='config_',
                dir=config_dir
            )

            # Write to temp file with fsync for durability
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                temp_fd = None  # fdopen now owns the fd
                json.dump(config_to_save, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is on disk

            # Atomic rename
            os.replace(temp_path, self.config_path)
            temp_path = None  # Successfully renamed

        except OSError as e:
            logger.error(f"Failed to save config (disk/permission error): {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
        finally:
            # Cleanup temp file on failure
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass
            if temp_path is not None and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get config value by dot-notation path.

        Example: config.get('download.concurrent_limit')
        """
        keys = key_path.split(".")

        with self._config_lock:
            value = self._config

            try:
                for key in keys:
                    value = value[key]
                return value
            except (KeyError, TypeError):
                return default

    def set(self, key_path: str, value: Any, save: bool = True):
        """
        Set config value by dot-notation path.

        Example: config.set('download.concurrent_limit', 5)
        """
        with self._config_lock:
            keys = key_path.split(".")
            target = self._config

            # Navigate to parent
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]

            # Set value
            target[keys[-1]] = value

        if save:
            self.save()

    def get_section(self, section: str) -> dict:
        """Get entire config section."""
        with self._config_lock:
            return deepcopy(self._config.get(section, {}))

    def set_section(self, section: str, values: dict, save: bool = True):
        """Set entire config section."""
        with self._config_lock:
            self._config[section] = deepcopy(values)
        if save:
            self.save()

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        with self._config_lock:
            self._config = deepcopy(DEFAULT_CONFIG)
            self._config["download"]["output_dir"] = str(get_default_output_dir())
        self.save()

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)."""
        if cls._instance is not None:
            with cls._instance._config_lock:
                cls._instance._cancel_queued_save_locked()
        cls._instance = None
