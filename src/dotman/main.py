#!/usr/bin/env python3
"""Dotman - A dotfile manager for symlinks and templates."""

import sys

from dotman.cli import app, console
from dotman.core.exceptions import DotmanError


def main() -> None:
    """Entry point for the dotman CLI."""
    try:
        app()
    except DotmanError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
