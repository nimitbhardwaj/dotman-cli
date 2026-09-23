"""CLI commands for Dotman using Typer."""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from dotman import __version__
from dotman.core.config import Config, get_repo_manager

console = Console()

app = typer.Typer(
    name="dotman",
    help="A dotfile manager for symlinks and templates.",
    no_args_is_help=True,
)
repo_app = typer.Typer(
    name="repo",
    help="Manage multiple dotfiles repositories.",
    no_args_is_help=True,
)


def get_config(
    config_dir: Path | None = None,
    backup_dir: str | None = None,
    template_suffix: str | None = None,
    repo_name: str | None = None,
) -> Config:
    """Get the configuration instance."""
    if config_dir is None:
        if os.environ.get("DOTMAN_CONFIG_DIR"):
            config_dir = Path(os.environ["DOTMAN_CONFIG_DIR"])

    if repo_name is not None:
        repo_manager = get_repo_manager()
        repo_config = repo_manager.get_repository(repo_name)
        config_dir = repo_config.path

    repo_dir = config_dir if config_dir is not None else Path.cwd()

    return Config(repo_dir, repo_name=repo_name)


def get_repository_option() -> Annotated[
    str | None,
    typer.Option(
        "--repo", "-r", help="Repository name (uses default if not specified)"
    ),
]:
    """Repository option for CLI commands."""
    return None


@app.callback(invoke_without_command=True)
def version_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version"),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit(0)


app.add_typer(repo_app)
