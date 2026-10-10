"""Retention controls for transient Gradio uploads and temporary inference composites."""

from __future__ import annotations

import logging
import shutil
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_transient_dir(directory: str | Path, data_dir: str | Path) -> Path:
    """Ensure cleanup can only target a dedicated directory, never a broad user path."""
    untrusted = Path(directory).expanduser()
    if untrusted.is_symlink():
        raise ValueError("GRADIO_TEMP_DIR cannot be a symlink")
    path = untrusted.resolve()
    data = Path(data_dir).expanduser().resolve()
    protected = {Path("/"), Path.home().resolve(), Path.cwd().resolve()}
    if path in protected or any(path in item.parents for item in protected):
        raise ValueError(f"GRADIO_TEMP_DIR is too broad for automatic cleanup: {path}")
    if path == data or path in data.parents:
        raise ValueError("GRADIO_TEMP_DIR cannot be the data directory or one of its parents")
    if data in path.parents:
        relative = path.relative_to(data)
        if relative.parts and relative.parts[0] in {"events", "objects", "fixtures", "exports"}:
            raise ValueError("GRADIO_TEMP_DIR cannot overlap retained evidence, references, or fixtures")
    return path


def directory_stats(root: str | Path) -> dict[str, int]:
    path = Path(root)
    total_bytes = file_count = 0
    if not path.exists():
        return {"files": 0, "bytes": 0}
    for entry in path.rglob("*"):
        try:
            if entry.is_file() and not entry.is_symlink():
                total_bytes += entry.stat().st_size
                file_count += 1
        except OSError as exc:
            logger.warning("Could not inspect transient file %s: %s", entry, exc)
    return {"files": file_count, "bytes": total_bytes}


def prune_transient_cache(
    root: str | Path,
    *,
    retention_seconds: float = 24 * 60 * 60,
    max_bytes: int = 2 * 1024 * 1024 * 1024,
    now: float | None = None,
) -> dict[str, int]:
    """Remove expired regular files, then oldest files if the directory exceeds its cap."""
    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    now = time.time() if now is None else now
    files: list[tuple[float, int, Path]] = []
    for entry in directory.rglob("*"):
        try:
            if entry.is_symlink():
                entry.unlink(missing_ok=True)
                continue
            if entry.is_file():
                stat = entry.stat()
                files.append((stat.st_mtime, stat.st_size, entry))
        except OSError as exc:
            logger.warning("Could not inspect transient file %s: %s", entry, exc)

    retained = []
    for modified, size, path in files:
        if now - modified > retention_seconds:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.error("Could not prune expired transient file %s: %s", path, exc)
                retained.append((modified, size, path))
        else:
            retained.append((modified, size, path))
    files = retained

    total = sum(size for _, size, _ in files)
    if total > max_bytes:
        for record in sorted(files):
            if total <= max_bytes:
                break
            _, size, path = record
            try:
                path.unlink(missing_ok=True)
                total -= size
            except OSError as exc:
                logger.error("Could not prune transient file %s to satisfy size cap: %s", path, exc)
    return directory_stats(directory)


class PrivacyJanitor:
    def __init__(
        self,
        directory: str | Path,
        *,
        retention_seconds: float = 24 * 60 * 60,
        max_bytes: int = 2 * 1024 * 1024 * 1024,
        interval_seconds: float = 600,
    ):
        self.directory = Path(directory)
        self.retention_seconds = retention_seconds
        self.max_bytes = max_bytes
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._stats = {"files": 0, "bytes": 0}
        self._lock = threading.Lock()

    def start(self) -> None:
        self._stats = prune_transient_cache(
            self.directory,
            retention_seconds=self.retention_seconds,
            max_bytes=self.max_bytes,
        )
        self._thread = threading.Thread(target=self._run, name="localrecall-privacy-janitor", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            stats = prune_transient_cache(
                self.directory,
                retention_seconds=self.retention_seconds,
                max_bytes=self.max_bytes,
            )
            with self._lock:
                self._stats = stats

    def stats(self) -> dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def clear(self) -> None:
        if self.directory.is_symlink():
            logger.error("Refusing to clear symlinked transient directory %s", self.directory)
            return
        if self.directory.exists():
            for path in self.directory.iterdir():
                try:
                    if path.is_dir() and not path.is_symlink():
                        shutil.rmtree(path)
                    else:
                        path.unlink(missing_ok=True)
                except OSError as exc:
                    logger.error("Could not clear transient cache path %s: %s", path, exc)
        with self._lock:
            self._stats = {"files": 0, "bytes": 0}

    def stop(self, *, clear: bool = True) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        if clear:
            self.clear()

