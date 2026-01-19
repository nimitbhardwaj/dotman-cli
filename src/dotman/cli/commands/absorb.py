"""Absorb command for dotman CLI."""

import re
from pathlib import Path
from typing import Annotated

import typer

from dotman.commands import app, console, get_config
from dotman.core.link_manager import LinkManager


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
