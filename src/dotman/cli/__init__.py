"""Shared CLI utilities and base module for Dotman."""

from dotman.cli.commands import (
    clone,
    deploy,
    init,
    list_packages,
    pull,
    push,
    status,
    undeploy,
)
from dotman.commands import (
    app,
    console,
    get_config,
    get_repository_option,
    repo_app,
)

__all__ = [
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
]
