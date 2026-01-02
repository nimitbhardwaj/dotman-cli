#!/usr/bin/env python3
"""Dotman - A dotfile manager for symlinks and templates."""

from dotman.cli import app


def main() -> None:
    """Entry point for the dotman CLI."""
    app()


if __name__ == "__main__":
    main()
