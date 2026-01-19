"""Init command for dotman CLI."""

from pathlib import Path
from typing import Annotated

import typer

from dotman.cli_utils import app, console, get_config
from dotman.core.config import get_repo_manager
from dotman.managers import RemoteManager


@app.command()
def init(
    repo_name: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Repository name for registration"),
    ] = None,
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", "-c", help="The path of config directory"),
    ] = None,
) -> None:
    """Initialize dotman configuration in the current directory.

    Creates a .dotman/ folder with global.yaml and local.yaml configs.
    Run this from your dotfiles repository root.
    """
    config = get_config(config_dir=config_dir)

    if config.is_initialized():
        console.print("[yellow]Dotman is already initialized.[/yellow]")
        console.print(f"Repo directory: {config.repo_dir}")
        console.print(f"Config directory: {config.dotman_dir}")
        return

    config.init()
    console.print("[green]Dotman initialized successfully![/green]")
    console.print(f"Repo directory: {config.repo_dir}")
    console.print(f"Config directory: {config.dotman_dir}")
    console.print(f"Config: {config.config_path}")
    console.print(f"Local config: {config.local_config_path}")

    if repo_name:
        try:
            repo_manager = get_repo_manager()
            remote_manager = RemoteManager(config.repo_dir)
            remote_url = (
                remote_manager.get_remote_url("origin")
                if remote_manager.is_git_repo()
                else None
            )
            repo_manager.register_repository(
                name=repo_name,
                path=config.repo_dir,
                remote_url=remote_url,
                set_default=True,
            )
            console.print(f"[green]Registered repository as '{repo_name}'[/green]")
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not register repository: {e}[/yellow]"
            )
