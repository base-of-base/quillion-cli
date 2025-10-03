import os
import time
import typing as t
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..debug.debugger import debugger


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback, config, debugger):
        self.restart_callback = restart_callback
        self.config = config
        self.debugger = debugger
        self.last_trigger = 0.0

    def _should_ignore(self, path: str) -> bool:
        normalized = path.replace("\\", "/")
        return any(pattern in normalized for pattern in self.config.ignore_patterns)

    def _should_watch(self, path: str) -> bool:
        if self._should_ignore(path):
            return False
        return Path(path).suffix in self.config.file_extensions

    def on_modified(self, event):
        if not event.is_directory and self._should_watch(event.src_path):
            current_time = time.time()
            if current_time - self.last_trigger > self.config.delay:
                self.last_trigger = current_time
                filename = os.path.basename(event.src_path)
                self.debugger.info(f"File changed: {filename}")
                time.sleep(0.1)
                self.restart_callback()


def setup_file_watchers(
    config, project_dir: str, restart_callback: t.Callable
) -> t.List[Observer]:
    """Set up file system watchers for hot reload"""
    observers = []
    dev_cfg = config.development

    for watch_dir in dev_cfg.watch_dirs:
        full_path = Path(project_dir) / watch_dir

        if full_path.exists():
            handler = FileChangeHandler(restart_callback, dev_cfg, debugger)
            observer = Observer()
            observer.schedule(handler, str(full_path), recursive=True)
            observer.start()
            observers.append(observer)
        else:
            debugger.warning(f"Watch directory not found: {full_path}")

    return observers


def shutdown_watchers(observers: t.List[Observer]):
    """Cleanup file watchers"""
    for observer in observers:
        observer.stop()
    for observer in observers:
        observer.join()
