"""CLI commands for Dotman using Typer."""

import os
from pathlib import Path

import typer
from rich.console import Console

from dotman import __version__
from dotman.core.config import Config, get_repo_manager
from dotman.core.exceptions import DotmanError

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
    repo_name: str | None = None,
) -> Config:
    """Resolve which dotfiles repository to use and load its configuration.

    Priority: --repo > --config-dir > $DOTMAN_CONFIG_DIR > cwd, and if cwd is
    not a dotman repo, the default registered repository.
    """
    if repo_name is not None:
        config_dir = get_repo_manager().get_repository(repo_name).path
    elif config_dir is None and os.environ.get("DOTMAN_CONFIG_DIR"):
        config_dir = Path(os.environ["DOTMAN_CONFIG_DIR"])
    elif config_dir is None and not Config(Path.cwd()).is_initialized():
        try:
            config_dir = get_repo_manager().get_repository(None).path
        except DotmanError:
            pass

    return Config(config_dir or Path.cwd(), repo_name=repo_name, backup_dir=backup_dir)


@app.callback(invoke_without_command=True)
def version_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version"),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit(0)


app.add_typer(repo_app)
