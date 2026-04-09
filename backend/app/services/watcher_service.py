"""
services/watcher_service.py - Monitors directories for file changes and
triggers the full spec + SDK regeneration pipeline.
"""

import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.core.config import settings
from app.core.logger import logger
from app.services.openapi_service import generate as generate_spec
from app.services.sdk_service import generate_all


class _ChangeHandler(FileSystemEventHandler):
    """Debounced handler that regenerates on .py file changes."""

    def __init__(self, model: str):
        super().__init__()
        self.model = model
        self._last_trigger = 0.0
        self._pending = False

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return

        now = time.time()
        if now - self._last_trigger < settings.watcher_debounce:
            self._pending = True
            return

        self._last_trigger = now
        self._regenerate(event.src_path)

    def _regenerate(self, filepath: str):
        # Brief delay — on Windows the file may still be locked by the writer
        time.sleep(0.5)

        logger.info("#" * 60)
        logger.info("change detected: %s", os.path.basename(filepath))
        logger.info("#" * 60)
        try:
            result = generate_spec(filepath, model=self.model)
            if result:
                generate_all(result["spec_path"])
                logger.info("regeneration complete")
            else:
                logger.warning("spec generation failed; SDKs unchanged")
        except PermissionError:
            logger.debug("file still locked, will retry on next debounce tick")
            self._pending = True
        except Exception as exc:
            logger.error("regeneration error: %s", exc)

    def tick(self):
        """Flush debounced events; call periodically."""
        if self._pending and time.time() - self._last_trigger >= settings.watcher_debounce:
            self._pending = False
            # Regenerate using default backend file
            default = settings.default_backend_file
            if os.path.isfile(default):
                self._regenerate(default)


def start_watcher(model: str = "") -> Observer:
    """
    Start a background file-system observer on sample_backend_dir.
    Returns the Observer instance (already started).
    """
    model = model or settings.ollama_model
    watch_dir = settings.sample_backend_dir

    if not os.path.isdir(watch_dir):
        os.makedirs(watch_dir, exist_ok=True)
        logger.warning("created watch directory: %s", watch_dir)

    handler = _ChangeHandler(model)
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=True)
    observer.daemon = True
    observer.start()

    logger.info("file watcher started on: %s", os.path.abspath(watch_dir))

    # Background tick thread for debounce flushing
    def _tick_loop():
        while observer.is_alive():
            handler.tick()
            time.sleep(1)

    tick_thread = threading.Thread(target=_tick_loop, daemon=True)
    tick_thread.start()

    return observer
