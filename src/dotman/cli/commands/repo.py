"""Repository management commands for dotman CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from dotman.cli_utils import console, repo_app
from dotman.core.config import Config, get_repo_manager
from dotman.core.exceptions import RepositoryNotFoundError


@repo_app.command(name="add")
def add_repository(
    name: Annotated[
        str,
        typer.Argument(help="Unique name for the repository"),
    ],
    path: Annotated[
        Path,
        typer.Argument(help="Path to the dotfiles repository"),
    ],
    remote_url: Annotated[
        str | None,
        typer.Option("--url", "-u", help="Optional remote URL"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--desc", "-d", help="Optional description"),
    ] = None,
    set_default: Annotated[
        bool,
        typer.Option("--default", help="Set as the default repository"),
    ] = False,
) -> None:
    """Register a dotfiles repository with dotman.

    Examples:
        dotman repo add work ~/dotfiles-work
        dotman repo add personal ~/dotfiles --url https://github.com/user/dotfiles
        dotman repo add work ~/dotfiles-work --default
    """
    repo_manager = get_repo_manager()

    if not path.exists():
        console.print(f"[red]Path does not exist: {path}[/red]")
        raise typer.Exit(1)

    try:
        config = Config(path)
        if not config.is_initialized():
            console.print(
                f"[yellow]Warning: {path} is not initialized with dotman.[/yellow]"
            )
            console.print("Run 'dotman init' in that directory first.")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    try:
        repo_manager.register_repository(
            name=name,
            path=path,
            remote_url=remote_url,
            description=description,
            set_default=set_default,
        )
        console.print(f"[green]Repository '{name}' added successfully![/green]")
        console.print(f"  Path: {path}")
        if remote_url:
            console.print(f"  Remote: {remote_url}")
        if set_default or repo_manager.registry.default_repo == name:
            console.print("  [cyan](default)[/cyan]")
    except Exception as e:
        console.print(f"[red]Error adding repository: {e}[/red]")
        raise typer.Exit(1)


@repo_app.command(name="remove")
def remove_repository(
    name: Annotated[
        str,
        typer.Argument(help="Name of the repository to remove"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Unregister a dotfiles repository from dotman.

    Examples:
        dotman repo remove work
        dotman repo remove work --force
    """
    repo_manager = get_repo_manager()

    repo = repo_manager.get_repository(name)
    if not repo:
        console.print(f"[red]Repository '{name}' not found.[/red]")
        raise typer.Exit(1)

    if not force:
        console.print(f"Unregister repository '{name}'?")
        console.print(f"  Path: {repo.path}")
        if not typer.confirm("Continue?"):
            raise typer.Exit(0)

    if repo_manager.unregister_repository(name):
        console.print(f"[green]Repository '{name}' removed.[/green]")
    else:
        console.print(f"[red]Failed to remove repository '{name}'.[/red]")
        raise typer.Exit(1)


@repo_app.command(name="list")
def list_repositories() -> None:
    """List all registered dotfiles repositories.

    Examples:
        dotman repo list
    """
    repo_manager = get_repo_manager()
    repos = repo_manager.list_repositories()

    if not repos:
        console.print("[yellow]No repositories registered.[/yellow]")
        console.print("Use 'dotman repo add <name> <path>' to add one.")
        return

    table = Table(title="Registered Repositories")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Remote", style="white")
    table.add_column("Default", style="white")

    for repo in repos:
        default_mark = "[green]*[/green]" if repo.is_default else ""
        remote = repo.remote_url or "-"
        table.add_row(repo.name, str(repo.path), remote, default_mark)

    console.print(table)
    console.print("\n[dim]* = default repository[/dim]")


@repo_app.command(name="default")
def set_default_repository(
    name: Annotated[
        str,
        typer.Argument(help="Name of the repository to set as default"),
    ],
) -> None:
    """Set the default repository.

    Examples:
        dotman repo default work
    """
    repo_manager = get_repo_manager()

    if repo_manager.set_default_repository(name):
        console.print(f"[green]Default repository set to '{name}'.[/green]")
    else:
        console.print(f"[red]Repository '{name}' not found.[/red]")
        raise typer.Exit(1)


@repo_app.command(name="show")
def show_repository(
    name: Annotated[
        str | None,
        typer.Argument(help="Repository name (default: current/default)"),
    ] = None,
) -> None:
    """Show details of a repository.

    Examples:
        dotman repo show
        dotman repo show work
    """
    repo_manager = get_repo_manager()

    try:
        repo = repo_manager.get_repository(name)
    except RepositoryNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Repository: {repo.name}[/bold]")
    console.print(f"  Path: {repo.path}")
    console.print(f"  Remote: {repo.remote_url or '(none)'}")
    console.print(f"  Description: {repo.description or '(none)'}")
    console.print(f"  Default: {'Yes' if repo.is_default else 'No'}")

    config = Config(repo.path)
    if config.is_initialized():
        packages = config.global_config.packages
        enabled = config.get_enabled_packages()
        console.print(f"\n  Packages: {len(packages)} defined, {len(enabled)} enabled")
        if packages:
            console.print("  Defined packages:")
            for pkg_name in list(packages.keys())[:5]:
                enabled_mark = "[green]*[/green]" if pkg_name in enabled else ""
                console.print(f"    - {pkg_name} {enabled_mark}")
            if len(packages) > 5:
                console.print(f"    ... and {len(packages) - 5} more")
    else:
        console.print("\n  [yellow]Not initialized with dotman[/yellow]")
