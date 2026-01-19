"""CLI commands for Dotman using Typer."""

import os
import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dotman.config import Config, get_repo_manager
from dotman.exceptions import RepositoryNotFoundError
from dotman.link_manager import LinkManager

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


def _should_skip_file(
    target_file: Path,
    absorb_ignore: list[str] | None,
    dest_file: Path,
) -> tuple[bool, str]:
    """Check if a file should be skipped during absorption.

    Returns:
        tuple: (should_skip, reason_for_skipping)
    """
    if target_file.is_symlink():
        return True, "symlink"
    if target_file.name.endswith(".j2"):
        return True, "template"
    if absorb_ignore and any(
        re.search(pattern, str(target_file)) for pattern in absorb_ignore
    ):
        return True, "ignored"
    if dest_file.exists():
        return True, "exists"
    return False, ""


def _absorb_file(
    target_file: Path,
    dest_file: Path,
    link_manager: LinkManager,
    dry_run: bool,
) -> None:
    """Absorb a single file from target to source and create symlink."""
    if not dry_run:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.rename(dest_file)
        link_manager._create_symlink(dest_file, target_file)


def _absorb_directory(
    target_file: Path,
    dest_file: Path,
    link_manager: LinkManager,
    dry_run: bool,
) -> None:
    """Absorb a directory from target to source and create symlink."""
    if dest_file.exists():
        if dest_file.is_dir():
            return  # Skip if directory already exists (created for nested files)
        # If it's a file (not directory), let it fail so user can investigate

    if not dry_run:
        dest_file.mkdir(parents=True, exist_ok=True)
        link_manager._create_symlink(dest_file, target_file)


@app.command(name="absorb")
def absorb_changes(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to deploy (default: all enabled)"),
    ] = None,
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", "-c", help="The path of config directory"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying them"),
    ] = False,
    backup_dir: Annotated[
        str | None,
        typer.Option("--backup-dir", help="Override backup directory"),
    ] = None,
    repo_name: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Repository name"),
    ] = None,
) -> None:
    """Absorb changes from deployed dotfiles back into the dotfiles repository."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)
    link_manager = LinkManager(config.backup_dir)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    packages_to_absorb = packages or config.get_enabled_packages()
    # Sort for deterministic behavior (first package wins conflicts)
    packages_to_absorb.sort()

    package_objs = []
    for package_name in packages_to_absorb:
        if (pkg := config.get_package(package_name)) is not None:
            package_objs.append(pkg)

    # Track which absolute target paths have been processed (first package wins)
    processed_targets: set[Path] = set()

    for package_obj in package_objs:
        for pkg_file in package_obj.files:
            source = config.dotfiles_dir / pkg_file.source
            target = Path(pkg_file.target).expanduser()
            absorb_ignore = pkg_file.absorb_ignore

            if not source.exists():
                console.print(
                    f"[yellow]Source file '{source}' does not exist, skipping.[/yellow]"
                )
                continue
            if not target.exists():
                console.print(
                    f"[yellow]Target file '{target}' does not exist, skipping.[/yellow]"
                )
                continue

            # First package wins: skip if this target was already processed
            if target in processed_targets:
                console.print(
                    f"[yellow]Target '{target}'"
                    f" already processed by earlier package, skipping.[/yellow]"
                )
                continue
            processed_targets.add(target)

            if target.is_dir():
                for target_file in target.rglob("*"):
                    relative_path = target_file.relative_to(target)
                    dest_file = source / relative_path

                    should_skip, _ = _should_skip_file(
                        target_file, absorb_ignore, dest_file
                    )
                    if should_skip:
                        continue

                    try:
                        if target_file.is_file():
                            # Skip if corresponding .j2 template exists in source
                            template_file = dest_file.with_suffix(
                                dest_file.suffix + ".j2"
                            )
                            if template_file.exists():
                                continue

                            _absorb_file(target_file, dest_file, link_manager, dry_run)
                            console.print(
                                f"[yellow]Absorbed file:[/yellow]"
                                f" {target_file} -> {dest_file}"
                            )
                        # Skip directories
                        # parent dirs are created when absorbing files
                    except Exception as e:
                        console.print(f"[red]Error absorbing file:[/red] {e}")

    console.print("[green]Absorb complete![/green]")


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


app.add_typer(repo_app)
