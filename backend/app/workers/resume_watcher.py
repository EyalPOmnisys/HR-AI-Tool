# app/workers/resume_watcher.py
"""
Resume File Watcher - Monitors resume directory and automatically processes new uploads.
Uses file system events to detect and ingest new resume files with debouncing to avoid duplicates.
"""
# Purpose: Watch backend/data/resumes/ and auto-ingest new files.
from __future__ import annotations

import time
from pathlib import Path
from typing import Set
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from app.db.base import SessionLocal
from app.services.resumes import ingestion_pipeline as resume_service

# Resolve /app/data/resumes inside container
BASE_DIR = Path(__file__).resolve().parents[2]  # /app
RESUME_DIR = BASE_DIR / "data" / "resumes"
RESUME_DIR.mkdir(parents=True, exist_ok=True)


class _EventHandler(FileSystemEventHandler):
    """
    Debounced file watcher that ignores temp/partial files and only processes
    a file once after its last write settled.
    """
    # Keep a small in-memory seen set to avoid rapid duplicate processing
    _seen_recent: Set[str] = set()
    _cooldown_sec: float = 1.0

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            self._process(Path(event.src_path))

    def on_modified(self, event):
        # Handle late writes (e.g., copying finishing)
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            self._process(Path(event.src_path))

    def _is_ignorable(self, path: Path) -> bool:
        name = path.name.lower()
        return (
            name.startswith("~$")
            or name.endswith(".tmp")
            or name.endswith(".part")
            or name.endswith(".crdownload")
            or name.endswith(".download")
        )

    def _process(self, path: Path):
        # Simple debounce: if we've just seen the same path, skip for a moment
        key = str(path)
        if key in self._seen_recent:
            return
        self._seen_recent.add(key)

        try:
            if self._is_ignorable(path):
                return
            if not path.exists() or path.is_dir():
                return

            # Try to open for read to ensure the writer released the lock.
            # If it fails we skip; next modification event will try again.
            try:
                path.open("rb").close()
            except Exception:
                return

            db = SessionLocal()
            try:
                resume = resume_service.run_full_ingestion(db, path)
                print(f"[Watcher] ✅ processed resume: {resume.id} ({path.name})")
            except Exception as e:
                print(f"[Watcher] ❌ error processing {path.name}: {e}")
            finally:
                db.close()
        finally:
            # Release debounce key after a short cooldown
            def _release():
                try:
                    time.sleep(self._cooldown_sec)
                finally:
                    self._seen_recent.discard(key)
            # Non-threaded simple sleep (keeps implementation minimal)
            _release()


def main():
    print(f"[Watcher] 👀 Watching directory: {RESUME_DIR}")
    event_handler = _EventHandler()

    # Scan for existing files on startup
    print(f"[Watcher] 🔎 Scanning for existing files...")
    existing_files = [
        p for p in RESUME_DIR.iterdir() 
        if p.is_file() and not event_handler._is_ignorable(p)
    ]
    print(f"[Watcher] Found {len(existing_files)} existing files. Processing...")
    
    for file_path in existing_files:
        event_handler._process(file_path)

    observer = Observer(timeout=1.0)
    observer.schedule(event_handler, str(RESUME_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
