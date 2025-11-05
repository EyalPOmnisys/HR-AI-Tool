# Purpose: Watch backend/data/resumes/ and auto-ingest new files.
from __future__ import annotations
import time
from pathlib import Path
from watchdog.observers.polling import PollingObserver as Observer   # ✅ שינוי חשוב!
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from app.db.base import SessionLocal
from app.services import resume_service

# resolve /app/data/resumes inside container
BASE_DIR = Path(__file__).resolve().parents[2]  # /app
RESUME_DIR = BASE_DIR / "data" / "resumes"
RESUME_DIR.mkdir(parents=True, exist_ok=True)


class _EventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            self._process(Path(event.src_path))

    def on_modified(self, event):
        # handle late writes (e.g., copy finishing)
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            self._process(Path(event.src_path))

    @staticmethod
    def _process(path: Path):
        # ignore temp files
        name = path.name.lower()
        if name.startswith("~$") or name.endswith(".tmp") or name.endswith(".part"):
            return

        db = SessionLocal()
        try:
            resume = resume_service.ingest_file(db, path)
            resume_service.parse_and_store(db, resume)
            resume_service.chunk_and_embed(db, resume)
            print(f"[Watcher] processed resume: {resume.id} — {path.name}")
        except Exception as e:
            print(f"[Watcher] error processing {path.name}: {e}")
        finally:
            db.close()


def main():
    print(f"[Watcher] Watching directory: {RESUME_DIR}")
    event_handler = _EventHandler()
    observer = Observer(timeout=1.0)  # ✅ סריקה כל שנייה
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
