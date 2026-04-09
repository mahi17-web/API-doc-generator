"""
watcher.py - Monitors backend files for changes, triggers spec + SDK regeneration.
Uses watchdog with debounce to avoid rapid-fire rebuilds.
"""

import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from generator import generate
from sdk_generator import generate_all

DEBOUNCE_SECS = 3


class _Handler(FileSystemEventHandler):
    """React to modifications of watched source files."""

    def __init__(self, watched: list, model: str):
        super().__init__()
        self.watched = [os.path.abspath(f) for f in watched]
        self.model = model
        self._last = 0.0
        self._pending = False

    def on_modified(self, event):
        if event.is_directory or os.path.abspath(event.src_path) not in self.watched:
            return
        now = time.time()
        if now - self._last < DEBOUNCE_SECS:
            self._pending = True
            return
        self._last = now
        self._run(event.src_path)

    def _run(self, path: str):
        print(f"\n{'#' * 60}")
        print(f"[watcher] change detected: {os.path.basename(path)}")
        print(f"{'#' * 60}")
        try:
            spec = generate(path, model=self.model)
            if spec:
                generate_all(spec)
                print("[watcher] regeneration complete")
            else:
                print("[watcher] spec generation failed, SDKs unchanged")
        except Exception as exc:
            print(f"[watcher] ERROR: {exc}")
        print("[watcher] watching ... (Ctrl+C to stop)\n")

    def tick(self):
        """Call periodically to flush debounced events."""
        if self._pending and time.time() - self._last >= DEBOUNCE_SECS:
            self._pending = False
            if self.watched:
                self._run(self.watched[0])


def watch(files: list, model: str = "llama3"):
    """Block and watch the given files for changes."""
    valid = [f for f in files if os.path.isfile(f)]
    if not valid:
        print("[watcher] no valid files to watch")
        return

    dirs = {os.path.dirname(os.path.abspath(f)) or "." for f in valid}
    handler = _Handler(valid, model)
    observer = Observer()
    for d in dirs:
        observer.schedule(handler, d, recursive=False)

    observer.start()
    for f in valid:
        print(f"[watcher] watching: {os.path.abspath(f)}")
    print("[watcher] started (Ctrl+C to stop)\n")

    try:
        while True:
            time.sleep(1)
            handler.tick()
    except KeyboardInterrupt:
        print("\n[watcher] stopping ...")
        observer.stop()
    observer.join()
    print("[watcher] stopped.")


if __name__ == "__main__":
    targets = sys.argv[1:] or ["sample_backend.py"]
    watch(targets)
