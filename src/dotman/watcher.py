"""File system watcher abstraction for Dotman.

Supports different backends:
- inotify on Linux
- kqueue on macOS
"""

import abc
import enum
import os
import sys
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotman.exceptions import WatcherBackendError

if TYPE_CHECKING:
    import inotify.adapters
    import inotify.constants


class WatchEventType(enum.Enum):
    """Types of file system events."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    ACCESSED = "accessed"


@dataclass
class WatchEvent:
    """A file system watch event."""

    path: Path
    event_type: WatchEventType
    is_directory: bool = False


class FileSystemWatcher(abc.ABC):
    """Abstract base class for file system watchers."""

    @abc.abstractmethod
    def add_path(self, path: Path, recursive: bool = False) -> None:
        """Add a path to watch.

        Args:
            path: The path to watch
            recursive: Whether to watch recursively (for directories)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_path(self, path: Path) -> None:
        """Remove a path from watching.

        Args:
            path: The path to stop watching
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_watching(self, path: Path) -> bool:
        """Check if a path is being watched.

        Args:
            path: The path to check

        Returns:
            True if the path is being watched
        """
        raise NotImplementedError

    @abc.abstractmethod
    def events(self, timeout: float | None = None) -> Generator[WatchEvent, None, None]:
        """Get the next batch of events.

        Args:
            timeout: Maximum time to wait for events in seconds.
                     None means block indefinitely.

        Yields:
            WatchEvent objects
        """
        raise NotImplementedError

    @abc.abstractmethod
    def close(self) -> None:
        """Close the watcher and release resources."""
        raise NotImplementedError


class InotifyWatcher(FileSystemWatcher):
    """File system watcher using inotify (Linux)."""

    def __init__(self):
        self._inotify: inotify.adapters.Inotify | None = None
        self._watched_paths: dict[int, Path] = {}
        self._path_to_wd: dict[Path, int] = {}

    def _init_inotify(self) -> None:
        """Initialize inotify instance."""
        try:
            import inotify.adapters

            self._inotify = inotify.adapters.Inotify()
        except ImportError as e:
            raise WatcherBackendError(
                "inotify library not installed. Install with: pip install inotify"
            ) from e

    def add_path(self, path: Path, recursive: bool = False) -> None:
        """Add a path to watch using inotify."""
        if self._inotify is None:
            self._init_inotify()

        path = path.resolve()
        mask = " ".join(
            [
                "IN_CREATE",
                "IN_MODIFY",
                "IN_DELETE",
                "IN_MOVED_FROM",
                "IN_MOVED_TO",
                "IN_ACCESS",
                "IN_ISDIR",
            ]
        )

        try:
            if self._inotify is not None:
                self._inotify.add_watch(str(path), mask=mask)
        except OSError as e:
            raise WatcherBackendError(f"Failed to add watch for {path}: {e}") from e

    def remove_path(self, path: Path) -> None:
        """Remove a path from watching."""
        if self._inotify is None:
            return

        path = path.resolve()
        if path in self._path_to_wd:
            wd = self._path_to_wd[path]
            try:
                if self._inotify is not None:
                    self._inotify.remove_watch(wd)
            except OSError:
                pass
            del self._path_to_wd[path]
            if wd in self._watched_paths:
                del self._watched_paths[wd]

    def is_watching(self, path: Path) -> bool:
        """Check if a path is being watched."""
        return path.resolve() in self._path_to_wd

    def events(self, timeout: float | None = None) -> Generator[WatchEvent, None, None]:
        """Get events from inotify."""
        if self._inotify is None:
            self._init_inotify()

        try:
            if self._inotify is None:
                return
            events = self._inotify.event_gen(yield_nones=False, timeout_s=timeout)
            for event in events:
                yield self._inotify_event_to_watch_event(event)
        except Exception as e:
            raise WatcherBackendError(f"Error reading events: {e}") from e

    def _inotify_event_to_watch_event(self, event) -> WatchEvent:
        """Convert inotify event to WatchEvent."""
        import inotify.constants

        event_type_str = event[1]
        path_str = event[3]
        path = Path(path_str)
        is_directory = bool(event[2] & inotify.constants.IN_ISDIR)

        if event_type_str == "IN_CREATE":
            event_type = WatchEventType.CREATED
        elif event_type_str == "IN_MODIFY":
            event_type = WatchEventType.MODIFIED
        elif event_type_str == "IN_DELETE":
            event_type = WatchEventType.DELETED
        elif event_type_str == "IN_MOVED_TO":
            event_type = WatchEventType.MOVED
        elif event_type_str == "IN_MOVED_FROM":
            event_type = WatchEventType.MOVED
        elif event_type_str == "IN_ACCESS":
            event_type = WatchEventType.ACCESSED
        else:
            event_type = WatchEventType.MODIFIED

        return WatchEvent(path=path, event_type=event_type, is_directory=is_directory)

    def close(self) -> None:
        """Close the inotify instance."""
        if self._inotify is not None:
            self._inotify = None
        self._watched_paths.clear()
        self._path_to_wd.clear()


class KqueueWatcher(FileSystemWatcher):
    """File system watcher using kqueue (macOS/BSD)."""

    def __init__(self):
        import select

        self._kqueue: select.kqueue | None = None
        self._watched_paths: dict[int, Path] = {}
        self._path_to_fd: dict[Path, int] = {}

    def _init_kqueue(self) -> None:
        """Initialize kqueue instance."""
        import select

        try:
            self._kqueue = select.kqueue()
        except (ImportError, AttributeError) as e:
            raise WatcherBackendError("kqueue not available on this platform") from e

    def add_path(self, path: Path, recursive: bool = False) -> None:
        """Add a path to watch using kqueue."""
        import select

        if self._kqueue is None:
            self._init_kqueue()

        path = path.resolve()

        try:
            fd = os.open(str(path), os.O_RDONLY | os.O_NONBLOCK)
        except OSError as e:
            raise WatcherBackendError(f"Failed to open {path}: {e}") from e

        try:
            event = select.kevent(
                fd,
                filter=select.KQ_FILTER_VNODE,
                flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
                fflags=(
                    select.KQ_NOTE_DELETE
                    | select.KQ_NOTE_WRITE
                    | select.KQ_NOTE_EXTEND
                    | select.KQ_NOTE_ATTRIB
                    | select.KQ_NOTE_LINK
                    | select.KQ_NOTE_RENAME
                    | select.KQ_NOTE_REVOKE
                ),
            )
            if self._kqueue is not None:
                self._kqueue.control([event], 0)
            self._watched_paths[fd] = path
            self._path_to_fd[path] = fd
        except OSError as e:
            os.close(fd)
            raise WatcherBackendError(f"Failed to add watch for {path}: {e}") from e

    def remove_path(self, path: Path) -> None:
        """Remove a path from watching."""
        import select

        if self._kqueue is None:
            return

        path = path.resolve()
        if path in self._path_to_fd:
            fd = self._path_to_fd[path]
            try:
                event = select.kevent(
                    fd,
                    filter=select.KQ_FILTER_VNODE,
                    flags=select.KQ_EV_DELETE,
                    fflags=0,
                )
                if self._kqueue is not None:
                    self._kqueue.control([event], 0)
            except OSError:
                pass
            finally:
                os.close(fd)
            del self._path_to_fd[path]
            if fd in self._watched_paths:
                del self._watched_paths[fd]

    def is_watching(self, path: Path) -> bool:
        """Check if a path is being watched."""
        return path.resolve() in self._path_to_fd

    def events(self, timeout: float | None = None) -> Generator[WatchEvent, None, None]:
        """Get events from kqueue."""

        if self._kqueue is None:
            self._init_kqueue()

        try:
            if self._kqueue is None:
                return
            kevents = self._kqueue.control(None, 16, timeout)
            for event in kevents:
                fd = event.ident
                if fd in self._watched_paths:
                    path = self._watched_paths[fd]
                    event_type = self._kqueue_event_to_watch_event(event)
                    if event_type is not None:
                        yield WatchEvent(
                            path=path,
                            event_type=event_type,
                            is_directory=False,
                        )
        except OSError as e:
            if e.args[0] == 4:  # Interrupted system call
                return
            raise WatcherBackendError(f"Error reading events: {e}") from e

    def _kqueue_event_to_watch_event(self, event) -> WatchEventType | None:
        """Convert kqueue event to WatchEventType."""
        import select

        fflags = event.fflags

        if fflags & select.KQ_NOTE_DELETE:
            return WatchEventType.DELETED
        elif fflags & select.KQ_NOTE_RENAME:
            return WatchEventType.MOVED
        elif fflags & (select.KQ_NOTE_WRITE | select.KQ_NOTE_EXTEND):
            return WatchEventType.MODIFIED
        elif fflags & select.KQ_NOTE_ATTRIB:
            return WatchEventType.MODIFIED
        elif fflags & select.KQ_NOTE_LINK:
            return WatchEventType.MODIFIED

        return None

    def close(self) -> None:
        """Close the kqueue instance."""
        if self._kqueue is not None:
            self._kqueue.close()
            self._kqueue = None
        for fd in list(self._path_to_fd.values()):
            try:
                os.close(fd)
            except OSError:
                pass
        self._watched_paths.clear()
        self._path_to_fd.clear()


class PollingWatcher(FileSystemWatcher):
    """File system watcher using polling (fallback for all platforms)."""

    def __init__(self, poll_interval: float = 0.5):
        """Initialize the polling watcher.

        Args:
            poll_interval: How often to check for changes (in seconds)
        """
        self._poll_interval = poll_interval
        self._watched_paths: dict[Path, dict[str, float | None]] = {}
        self._event_queue: list[WatchEvent] = []

    def add_path(self, path: Path, recursive: bool = False) -> None:
        """Add a path to watch."""
        path = path.resolve()
        if path.is_file():
            try:
                mtime = path.stat().st_mtime
                self._watched_paths[path] = {"mtime": mtime, "ctime": None}
            except OSError:
                pass
        elif path.is_dir():
            self._watched_paths[path] = {"mtime": None, "ctime": None}
            if recursive:
                self._scan_directory(path)

    def _scan_directory(self, path: Path) -> None:
        """Scan a directory and add all files."""
        try:
            for root, dirs, files in os.walk(path):
                root_path = Path(root)
                for f in files:
                    file_path = (root_path / f).resolve()
                    if file_path not in self._watched_paths:
                        try:
                            mtime = file_path.stat().st_mtime
                            self._watched_paths[file_path] = {
                                "mtime": mtime,
                                "ctime": None,
                            }
                        except OSError:
                            pass
        except OSError:
            pass

    def remove_path(self, path: Path) -> None:
        """Remove a path from watching."""
        path = path.resolve()
        if path in self._watched_paths:
            del self._watched_paths[path]

    def is_watching(self, path: Path) -> bool:
        """Check if a path is being watched."""
        return path.resolve() in self._watched_paths

    def events(self, timeout: float | None = None) -> Generator[WatchEvent, None, None]:
        """Get events by polling."""
        import time

        start_time = time.monotonic()
        deadline = None if timeout is None else start_time + timeout

        while True:
            now = time.monotonic()
            if deadline is not None and now >= deadline:
                return

            for path in list(self._watched_paths.keys()):
                if not path.exists():
                    yield WatchEvent(path=path, event_type=WatchEventType.DELETED)
                    del self._watched_paths[path]
                else:
                    try:
                        stat = path.stat()
                        current_mtime = stat.st_mtime

                        if path in self._watched_paths:
                            saved = self._watched_paths[path]
                            saved_mtime = saved["mtime"]

                            if saved_mtime is not None and current_mtime > saved_mtime:
                                yield WatchEvent(
                                    path=path,
                                    event_type=WatchEventType.MODIFIED,
                                )
                                saved["mtime"] = current_mtime
                            elif saved_mtime is None:
                                saved["mtime"] = current_mtime
                    except OSError:
                        pass

            if self._event_queue:
                while self._event_queue:
                    yield self._event_queue.pop(0)

            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return
                time.sleep(min(self._poll_interval, remaining))
            else:
                time.sleep(self._poll_interval)

    def close(self) -> None:
        """Close the watcher."""
        self._watched_paths.clear()
        self._event_queue.clear()


def create_watcher() -> FileSystemWatcher:
    """Create an appropriate file system watcher for the current platform.

    Returns:
        A FileSystemWatcher instance appropriate for the current platform
    """
    if sys.platform == "linux":
        return InotifyWatcher()
    elif sys.platform == "darwin":
        return KqueueWatcher()
    else:
        return PollingWatcher()
