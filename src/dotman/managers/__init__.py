"""Operational managers for Dotman.

Provides managers for remote repositories, repository registry, deployment history,
and file system watching.
"""

from dotman.managers.history import (
    DeployedFile,
    DeploymentHistory,
    DeploymentRecord,
    HistoryManager,
)
from dotman.managers.remote import (
    RemoteManager,
    RemoteRepoConfig,
    detect_remote_from_string,
)
from dotman.managers.repository import (
    RepoManager,
    RepositoryConfig,
    RepositoryRegistry,
)
from dotman.managers.watcher import (
    FileSystemWatcher,
    InotifyWatcher,
    KqueueWatcher,
    PollingWatcher,
    WatchEvent,
    WatchEventType,
    create_watcher,
)

__all__ = [
    "DeployedFile",
    "DeploymentHistory",
    "DeploymentRecord",
    "HistoryManager",
    "RemoteManager",
    "RemoteRepoConfig",
    "detect_remote_from_string",
    "RepoManager",
    "RepositoryConfig",
    "RepositoryRegistry",
    "FileSystemWatcher",
    "InotifyWatcher",
    "KqueueWatcher",
    "PollingWatcher",
    "WatchEvent",
    "WatchEventType",
    "create_watcher",
]
