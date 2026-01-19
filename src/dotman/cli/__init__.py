"""Shared CLI utilities and base module for Dotman."""

from dotman.commands import (
    app,
    console,
    get_config,
    get_repository_option,
    repo_app,
)

__all__ = ["app", "console", "get_config", "get_repository_option", "repo_app"]
