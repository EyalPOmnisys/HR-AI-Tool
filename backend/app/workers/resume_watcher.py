# app/workers/resume_watcher.py
"""
Resume File Watcher - Monitors resume directory and automatically processes new uploads.
Uses file system events to detect and ingest new resume files with debouncing to avoid duplicates.
"""
# Purpose: Watch backend/data/resumes/ and auto-ingest new files.
from __future__ import annotations

import time
from pathlib import Path
from typing import Set, List
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from app.db.base import SessionLocal
from app.models.resume import Resume
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
                # print(f"[Watcher] ⏳ Processing started: {path.name}")
                resume = resume_service.run_full_ingestion(db, path)
                if resume.status == 'ready':
                    print(f"[Watcher] ✅ Success: {path.name}")
                elif resume.status == 'error':
                    print(f"[Watcher] ❌ Failed: {path.name}")
                # Else it was skipped (silent)
            except Exception as e:
                print(f"[Watcher] 💥 Exception: {path.name} - {e}")
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


def _reset_stuck_jobs():
    """
    Self-Healing: Detects jobs that were interrupted by a server crash.
    ONE STRIKE POLICY: Mark them as ERROR (Blacklist) to prevent infinite loops.
    """
    print("----------------------------------------------------------------")
    print("[Watcher] 🧹 STEP 1: Self-Healing Cleanup (One Strike Policy)")
    print("----------------------------------------------------------------")
    db = SessionLocal()
    try:
        # Find resumes that are stuck in active states
        # We include 'processing', 'extracting', 'parsing', 'embedding' or None
        stuck_resumes = db.query(Resume).filter(
            Resume.status.in_(['processing', 'extracting', 'parsing', 'embedding']) | (Resume.status == None)
        ).all()

        if stuck_resumes:
            print(f"[Watcher] ⚠️  Found {len(stuck_resumes)} stuck jobs from previous runs.")
            for resume in stuck_resumes:
                print(f"[Watcher] 💀 Marking stuck file as ERROR (Blacklist): {resume.file_path}")
                # Move straight to error. Do not pass Go. Do not collect $200.
                resume.status = 'error'
                resume.error_log = "System crash or interruption during processing. File blacklisted."
            
            db.commit()
            print(f"[Watcher] ✅ Cleanup complete. {len(stuck_resumes)} jobs blacklisted.")
        else:
            print("[Watcher] ✅ No stuck jobs found. System is clean.")
            
    except Exception as e:
        print(f"[Watcher] ❌ Error during startup cleanup: {e}")
    finally:
        db.close()


def main():
    print("================================================================")
    print(f"[Watcher] 👀 STARTING RESUME WATCHER")
    print(f"[Watcher] 📂 Directory: {RESUME_DIR}")
    print("================================================================")
    
    # 1. Run Self-Healing Cleanup FIRST
    _reset_stuck_jobs()

    event_handler = _EventHandler()

    # ---------------------------------------------------------
    # 2. SMART STARTUP SCAN
    # ---------------------------------------------------------
    print("\n----------------------------------------------------------------")
    print("[Watcher] 🧠 STEP 2: Smart Startup Scan")
    print("----------------------------------------------------------------")
    print(f"[Watcher] 📥 Loading known filenames from Database...")
    
    db = SessionLocal()
    known_filenames = set()
    try:
        # SECOND CHANCE: files that previously errored get one retry per watcher
        # restart. A restart usually means code/model changed - the bug that
        # blacklisted them may be fixed. Delete the error rows so the scan below
        # re-ingests those files cleanly (the content-hash skip would otherwise
        # block them forever). No infinite loop: within a run it is still one strike.
        error_rows = db.query(Resume).filter(Resume.status == 'error').all()
        retried = 0
        for row in error_rows:
            if row.file_path and Path(row.file_path).exists():
                print(f"[Watcher] 🔁 Second chance: clearing error record for {Path(row.file_path).name}")
                db.delete(row)
                retried += 1
        if retried:
            db.commit()
            print(f"[Watcher] 🔁 {retried} previously-failed files queued for retry.")

        # Fetch only file paths
        results = db.query(Resume.file_path).all()
        for r in results:
            if r.file_path:
                known_filenames.add(Path(r.file_path).name)
    finally:
        db.close()

    print(f"[Watcher] ℹ️  Database contains {len(known_filenames)} known files.")
    print(f"[Watcher] 🔎 Scanning physical directory for new files...")

    existing_files_on_disk = [
        p for p in RESUME_DIR.iterdir() 
        if p.is_file() and not event_handler._is_ignorable(p)
    ]

    print(f"[Watcher] ℹ️  Found {len(existing_files_on_disk)} files in directory.")

    # Phase A: Identify New Files (No Processing yet)
    new_files_queue: List[Path] = []
    skipped_count = 0

    for file_path in existing_files_on_disk:
        if file_path.name in known_filenames:
            skipped_count += 1
        else:
            new_files_queue.append(file_path)

    # Phase B: Process New Files with Progress Bar
    total_new = len(new_files_queue)
    
    print(f"[Watcher] 📊 Scan Result: {skipped_count} existing (skipped), {total_new} NEW files to process.")

    if total_new > 0:
        print(f"[Watcher] 🚀 Starting batch processing of {total_new} files...")
        for i, file_path in enumerate(new_files_queue, 1):
            remaining = total_new - i
            # print(f"[Watcher] ▶️  Batch Progress: Processing {i}/{total_new} (Remaining: {remaining}) >> {file_path.name}")
            if i % 10 == 0:
                print(f"[Watcher] 📊 Progress: {i}/{total_new} files scanned...")
            event_handler._process(file_path)
    else:
        print("[Watcher] ✨ No new files to process.")

    print(f"[Watcher] ✅ Smart Scan Complete.")
    print("==================================================")
    print("[Watcher] 👂 Listening for new file events...")
    # ---------------------------------------------------------

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
