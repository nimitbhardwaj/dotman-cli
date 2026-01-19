"""Pull command for dotman CLI."""

from pathlib import Path
from typing import Annotated

import typer

from dotman.commands import app, console, get_config
from dotman.core.exceptions import RemoteFetchError
from dotman.remote import RemoteManager


@app.command()
def pull(
    remote: Annotated[
        str | None,
        typer.Argument(help="Remote name (default: origin)"),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch to pull"),
    ] = None,
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", "-c", help="The path of config directory"),
    ] = None,
    repo_name: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Repository name"),
    ] = None,
) -> None:
    """Pull changes from the remote repository.

    Examples:
        dotman pull
        dotman pull origin
        dotman pull origin main
        dotman pull --repo work
    """
    config = get_config(config_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    remote_manager = RemoteManager(config.repo_dir)

    if not remote_manager.is_git_repo():
        console.print("[red]This is not a git repository.[/red]")
        raise typer.Exit(1)

    remote_name = remote or "origin"
    pull_branch = branch

    if pull_branch is None:
        pull_branch = remote_manager.get_current_branch()
        console.print(f"[cyan]Using current branch: {pull_branch}[/cyan]")

    try:
        remote_url = remote_manager.get_remote_url(remote_name)
        console.print(f"[cyan]Pulling from: {remote_name} ({remote_url})[/cyan]")
        console.print(f"  Branch: {pull_branch}")

        remote_manager.pull(remote=remote_name, branch=pull_branch)

        console.print("[green]Successfully pulled from remote![/green]")
    except RemoteFetchError as e:
        console.print(f"[red]Pull failed:[/red] {e}")
        raise typer.Exit(1)
