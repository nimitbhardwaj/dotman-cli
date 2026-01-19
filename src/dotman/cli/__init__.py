"""Shared CLI utilities and base module for Dotman."""

from dotman.cli.commands import (
    absorb_changes,
    clone,
    deploy,
    history,
    init,
    list_packages,
    pull,
    push,
    rollback,
    status,
    undeploy,
    watch,
)
from dotman.commands import (
    app,
    console,
    get_config,
    get_repository_option,
    repo_app,
)

__all__ = [
    "absorb_changes",
    "app",
    "console",
    "get_config",
    "get_repository_option",
    "repo_app",
    "init",
    "clone",
    "push",
    "pull",
    "deploy",
    "undeploy",
    "status",
    "list_packages",
    "history",
    "rollback",
    "watch",
]
