"""Tests for the file system watcher module."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from dotman.watcher import (
    FileSystemWatcher,
    PollingWatcher,
    WatcherBackendError,
    WatchEvent,
    WatchEventType,
    create_watcher,
)


class TestWatchEventType:
    """Tests for WatchEventType enum."""

    def test_event_types_exist(self):
        """Check all expected event types exist."""
        assert WatchEventType.CREATED.value == "created"
        assert WatchEventType.MODIFIED.value == "modified"
        assert WatchEventType.DELETED.value == "deleted"
        assert WatchEventType.MOVED.value == "moved"
        assert WatchEventType.ACCESSED.value == "accessed"


class TestWatchEvent:
    """Tests for WatchEvent dataclass."""

    def test_create_watch_event(self):
        """Check WatchEvent can be created with required fields."""
        path = Path("/test/path")
        event = WatchEvent(path=path, event_type=WatchEventType.MODIFIED)

        assert event.path == path
        assert event.event_type == WatchEventType.MODIFIED
        assert event.is_directory is False

    def test_create_watch_event_with_directory_flag(self):
        """Check WatchEvent can be created with is_directory=True."""
        path = Path("/test/path")
        event = WatchEvent(
            path=path, event_type=WatchEventType.CREATED, is_directory=True
        )

        assert event.path == path
        assert event.event_type == WatchEventType.CREATED
        assert event.is_directory is True


class TestFileSystemWatcher:
    """Tests for the abstract FileSystemWatcher class."""

    def test_is_abstract_base_class(self):
        """Check FileSystemWatcher is an abstract base class."""
        with pytest.raises(TypeError):
            FileSystemWatcher()


class TestPollingWatcher:
    """Tests for the PollingWatcher implementation."""

    def test_create_watcher(self):
        """Check PollingWatcher can be created."""
        watcher = PollingWatcher()
        assert watcher is not None

    def test_create_watcher_with_custom_poll_interval(self):
        """Check PollingWatcher accepts custom poll interval."""
        watcher = PollingWatcher(poll_interval=0.1)
        assert watcher is not None

    def test_add_path_file(self):
        """Check adding a file path to watch."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            watcher = PollingWatcher(poll_interval=0.05)
            watcher.add_path(temp_path)
            assert watcher.is_watching(temp_path)
        finally:
            os.unlink(temp_path)

    def test_add_path_directory(self):
        """Check adding a directory path to watch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            watcher = PollingWatcher(poll_interval=0.05)
            watcher.add_path(temp_path)
            assert watcher.is_watching(temp_path)

    def test_add_path_recursive(self):
        """Check adding a directory recursively."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            subdir = temp_path / "subdir"
            subdir.mkdir()
            test_file = subdir / "test.txt"
            test_file.write_text("test")

            watcher = PollingWatcher(poll_interval=0.05)
            watcher.add_path(temp_path, recursive=True)

            assert watcher.is_watching(temp_path)
            assert watcher.is_watching(test_file)

    def test_remove_path(self):
        """Check removing a path from watching."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            watcher = PollingWatcher(poll_interval=0.05)
            watcher.add_path(temp_path)
            assert watcher.is_watching(temp_path)

            watcher.remove_path(temp_path)
            assert not watcher.is_watching(temp_path)
        finally:
            os.unlink(temp_path)

    def test_is_watching_false_for_unwatched_path(self):
        """Check is_watching returns False for unwatched paths."""
        watcher = PollingWatcher(poll_interval=0.05)
        assert not watcher.is_watching(Path("/nonexistent/path"))

    def test_close_clears_watched_paths(self):
        """Check close clears all watched paths."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            watcher = PollingWatcher(poll_interval=0.05)
            watcher.add_path(temp_path)
            assert watcher.is_watching(temp_path)

            watcher.close()
            assert not watcher.is_watching(temp_path)
        finally:
            os.unlink(temp_path)

    def test_events_detects_file_modification(self):
        """Check watcher detects file modifications."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("initial content")
            temp_path = Path(f.name)

        try:
            watcher = PollingWatcher(poll_interval=0.02)
            watcher.add_path(temp_path)

            time.sleep(0.05)

            temp_path.write_text("modified content")

            events = []
            for event in watcher.events(timeout=1.5):
                events.append(event)
                if len(events) >= 2:
                    break

            assert len(events) >= 1
        finally:
            os.unlink(temp_path)

    def test_events_detects_file_deletion(self):
        """Check watcher detects file deletions."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            watcher = PollingWatcher(poll_interval=0.02)
            watcher.add_path(temp_path)

            time.sleep(0.05)

            os.unlink(temp_path)

            events = []
            for event in watcher.events(timeout=1.5):
                events.append(event)
                if len(events) >= 2:
                    break

            assert len(events) >= 1
        finally:
            if temp_path.exists():
                os.unlink(temp_path)

    def test_events_timeout_returns_empty(self):
        """Check events returns empty when timeout expires with no changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            watcher = PollingWatcher(poll_interval=0.05)
            watcher.add_path(Path(temp_dir))

            events = list(watcher.events(timeout=0.2))
            assert len(events) == 0

    def test_events_generator_can_be_exhausted(self):
        """Check events generator works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            watcher = PollingWatcher(poll_interval=0.02)
            watcher.add_path(temp_path)

            events = list(watcher.events(timeout=0.1))
            assert len(events) == 0


class TestCreateWatcher:
    """Tests for the create_watcher factory function."""

    def test_create_watcher_returns_appropriate_type(self):
        """Check create_watcher returns appropriate watcher for current platform."""
        import sys

        watcher = create_watcher()
        assert watcher is not None

        if sys.platform == "linux":
            from dotman.watcher import InotifyWatcher

            assert isinstance(watcher, InotifyWatcher)
        elif sys.platform == "darwin":
            from dotman.watcher import KqueueWatcher

            assert isinstance(watcher, KqueueWatcher)
        else:
            assert isinstance(watcher, PollingWatcher)

    def test_create_watcher_is_reusable(self):
        """Check create_watcher can be called multiple times."""
        import sys

        watcher1 = create_watcher()
        watcher2 = create_watcher()
        assert watcher1 is not None
        assert watcher2 is not None
        assert watcher1 is not watcher2

        if sys.platform == "linux":
            from dotman.watcher import InotifyWatcher

            assert isinstance(watcher1, InotifyWatcher)
            assert isinstance(watcher2, InotifyWatcher)
        elif sys.platform == "darwin":
            from dotman.watcher import KqueueWatcher

            assert isinstance(watcher1, KqueueWatcher)
            assert isinstance(watcher2, KqueueWatcher)
        else:
            assert isinstance(watcher1, PollingWatcher)
            assert isinstance(watcher2, PollingWatcher)

    def test_create_watcher_returns_polling_on_unknown(self):
        """Check create_watcher returns PollingWatcher on unknown platforms."""
        import sys

        original_platform = sys.platform

        try:
            sys.platform = "unknown"
            watcher = create_watcher()
            assert isinstance(watcher, PollingWatcher)
        finally:
            sys.platform = original_platform


class TestWatcherExceptions:
    """Tests for watcher-related exceptions."""

    def test_watcher_backend_error_is_dotman_error(self):
        """Check WatcherBackendError is a DotmanError."""
        from dotman.exceptions import DotmanError

        error = WatcherBackendError("test error")
        assert isinstance(error, DotmanError)
        assert str(error) == "test error"

    def test_watcher_backend_error_with_cause(self):
        """Check WatcherBackendError can be raised with a cause."""
        original_error = ValueError("original error")
        error = WatcherBackendError("test error")
        error.__cause__ = original_error

        assert error.__cause__ is original_error
