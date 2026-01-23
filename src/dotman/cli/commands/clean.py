"""Clean commands for dotman CLI."""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.tree import Tree

from dotman.cli_utils import app, console, get_config


def find_empty_dirs(root: Path) -> list[Path]:
    """Find all empty directories under the given root directory.

    Args:
        root: The root directory to search for empty directories.

    Returns:
        A list of Path objects pointing to empty directories, sorted.
    """
    empty_dirs: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        if dirpath != str(root) and not dirnames and not filenames:
            empty_dirs.append(Path(dirpath))

    empty_dirs.sort()
    return empty_dirs


def find_orphaned_symlinks(root: Path) -> list[Path]:
    """Find all orphaned symlinks under the given root directory.

    Args:
        root: The root directory to search for orphaned symlinks.

    Returns:
        A list of Path objects pointing to orphaned symlinks.
    """
    orphaned: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in (*dirnames, *filenames):
            path = Path(dirpath) / name

            if path.is_symlink():
                try:
                    resolved = path.resolve()
                    if not resolved.exists():
                        orphaned.append(path)
                except (OSError, RuntimeError):
                    orphaned.append(path)

    return orphaned


@app.command(name="clean")
def clean(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to clean (default: all)"),
    ] = None,
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", "-c", help="The path of config directory"),
    ] = None,
    backup_dir: Annotated[
        str | None,
        typer.Option("--backup-dir", help="Override backup directory"),
    ] = None,
    repo_name: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Repository name"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Show what would be removed without removing"
        ),
    ] = False,
) -> None:
    """Clean up deployment artifacts and temporary files."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    packages_to_clean = packages or config.get_enabled_packages()

    if not packages_to_clean:
        console.print("[yellow]No packages to clean.[/yellow]")
        return

    orphaned_symlinks: dict[str, list[Path]] = {}
    empty_dirs: dict[str, list[Path]] = {}

    for pkg_name in packages_to_clean:
        pkg = config.get_package(pkg_name)
        if not pkg:
            console.print(
                f"[yellow]Package '{pkg_name}' not found in config, skipping.[/yellow]"
            )
            continue

        for file_mapping in pkg.files:
            target = Path(file_mapping.target).expanduser()

            if target.is_dir():
                target_dir = target
                if target_dir.exists():
                    orphaned = find_orphaned_symlinks(target_dir)
                    empty = find_empty_dirs(target_dir)

                    if orphaned:
                        orphaned_symlinks[pkg_name] = orphaned
                    if empty:
                        empty_dirs[pkg_name] = empty
            elif target.is_file() or target.exists() or target.is_symlink():
                # For file targets, check if the file itself is an orphaned symlink
                if target.is_symlink():
                    try:
                        if not target.resolve().exists():
                            orphaned_symlinks.setdefault(pkg_name, []).append(target)
                    except (OSError, RuntimeError):
                        orphaned_symlinks.setdefault(pkg_name, []).append(target)

    total_orphaned = sum(len(v) for v in orphaned_symlinks.values())
    total_empty = sum(len(v) for v in empty_dirs.values())

    if total_orphaned == 0 and total_empty == 0:
        console.print("[green]No orphaned symlinks or empty directories found.[/green]")
        return

    tree = Tree("Cleanup Summary")

    if orphaned_symlinks:
        orphaned_tree = tree.add(f"Orphaned Symlinks ({total_orphaned})")
        for pkg_name, paths in orphaned_symlinks.items():
            pkg_tree = orphaned_tree.add(f"[cyan]{pkg_name}[/cyan]")
            for path in paths:
                pkg_tree.add(f"[red]{path}[/red]")

    if empty_dirs:
        empty_tree = tree.add(f"Empty Directories ({total_empty})")
        for pkg_name, dirs in empty_dirs.items():
            pkg_tree = empty_tree.add(f"[cyan]{pkg_name}[/cyan]")
            for dir_path in dirs:
                pkg_tree.add(f"[yellow]{dir_path}[/yellow]")

    console.print(tree)

    if dry_run:
        console.print("[cyan]Dry run mode - no changes will be made[/cyan]")

    if not dry_run and not typer.confirm("Proceed with cleanup?"):
        console.print("[yellow]Cleanup cancelled.[/yellow]")
        raise typer.Exit(0)

    removed_orphaned = 0
    removed_empty = 0

    for pkg_name, paths in orphaned_symlinks.items():
        for path in paths:
            try:
                if dry_run:
                    console.print(f"  [cyan]Would remove:[/cyan] {path}")
                else:
                    path.unlink()
                    removed_orphaned += 1
                    console.print(f"  [green]Removed:[/green] {path}")
            except OSError as e:
                console.print(f"  [red]Failed to remove {path}: {e}[/red]")

    for pkg_name, dirs in empty_dirs.items():
        for dir_path in sorted(dirs, reverse=True):
            try:
                if dry_run:
                    console.print(f"  [cyan]Would remove:[/cyan] {dir_path}")
                else:
                    dir_path.rmdir()
                    removed_empty += 1
                    console.print(f"  [green]Removed:[/green] {dir_path}")
            except OSError as e:
                console.print(f"  [yellow]Could not remove {dir_path}: {e}[/yellow]")

    if dry_run:
        console.print("\n[cyan]Dry run complete - no changes were made[/cyan]")
    else:
        console.print("\n[green]Clean complete![/green]")
        console.print(
            f"[dim]Removed {removed_orphaned} orphaned symlinks"
            f" and {removed_empty} empty directories.[/dim]"
        )
