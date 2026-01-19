"""Clone command for dotman CLI."""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer

from dotman.cli_utils import app, console, get_config
from dotman.core.exceptions import (
    RemoteAuthenticationError,
    RemoteCloneError,
    RemoteNotFoundError,
)
from dotman.managers import RemoteManager, detect_remote_from_string


@app.command()
def clone(
    repository: Annotated[
        str,
        typer.Argument(help="Repository URL or shorthand (e.g., user/repo)"),
    ],
    target_dir: Annotated[
        Path | None,
        typer.Argument(help="Target directory for the clone"),
    ] = None,
    branch: Annotated[
        str,
        typer.Option("--branch", "-b", help="Branch to clone"),
    ] = "main",
    auth_token: Annotated[
        str | None,
        typer.Option(
            "--auth-token", "-t", help="Authentication token for private repos"
        ),
    ] = None,
    shallow: Annotated[
        bool,
        typer.Option("--shallow", help="Perform a shallow clone"),
    ] = False,
    init: Annotated[
        bool,
        typer.Option("--init", help="Initialize dotman in the cloned repository"),
    ] = False,
) -> None:
    """Clone a remote dotfiles repository.

    Supports GitHub (user/repo or full URL) and GitLab repositories.

    Examples:
        dotman clone user/dotfiles
        dotman clone https://github.com/user/dotfiles.git
        dotman clone user/dotfiles --branch develop --init
    """
    url = detect_remote_from_string(repository)

    if target_dir is None:
        parsed = urlparse(url)
        repo_name = Path(parsed.path).stem
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        target_dir = Path.cwd() / repo_name

    if target_dir.exists():
        console.print(f"[yellow]Target directory already exists: {target_dir}[/yellow]")
        raise typer.Exit(1)

    depth = 1 if shallow else None

    console.print(f"[cyan]Cloning repository: {url}[/cyan]")
    console.print(f"  Branch: {branch}")
    console.print(f"  Target: {target_dir}")

    try:
        remote_manager = RemoteManager(target_dir.parent)
        remote_manager.clone(
            url=url,
            target_dir=target_dir,
            branch=branch,
            auth_token=auth_token,
            depth=depth,
        )
    except RemoteNotFoundError as e:
        console.print(f"[red]Repository not found:[/red] {e}")
        raise typer.Exit(1)
    except RemoteAuthenticationError as e:
        console.print(f"[red]Authentication failed:[/red] {e}")
        console.print("Provide a valid auth token with --auth-token")
        raise typer.Exit(1)
    except RemoteCloneError as e:
        console.print(f"[red]Clone failed:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"[green]Successfully cloned to: {target_dir}[/green]")

    if init:
        config = get_config(config_dir=target_dir)
        if not config.is_initialized():
            config.init()
            console.print("[green]Dotman initialized in cloned repository[/green]")
        else:
            console.print(
                "[yellow]Dotman already initialized in cloned repository[/yellow]"
            )
