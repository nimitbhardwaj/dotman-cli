"""Diff command for dotman CLI."""

import difflib
from pathlib import Path
from typing import Annotated

import typer
from rich.syntax import Syntax

from dotman.cli_utils import app, console, get_config
from dotman.core.exceptions import DotmanError
from dotman.core.link_manager import LinkManager
from dotman.core.template_engine import TemplateEngine


@app.command()
def diff(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to diff (default: all enabled)"),
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
    """Show what deploy would change in rendered templates and conflicting files.

    Exits with 1 when differences are found, so it can be used in scripts.
    """
    config = get_config(config_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    link_manager = LinkManager(config.backup_dir)
    template_engine = TemplateEngine()
    found = False

    for pkg_name in packages or config.get_enabled_packages():
        pkg = config.get_package(pkg_name)
        if not pkg:
            console.print(f"[yellow]Package '{pkg_name}' not found, skipping.[/yellow]")
            continue
        variables = config.get_merged_variables(pkg_name)

        for file_mapping in pkg.files:
            source = config.dotfiles_dir / file_mapping.source
            target = Path(file_mapping.target).expanduser()
            if source.is_dir():
                pairs = [
                    (f, link_manager.derive_target(f, source, target))
                    for f in source.rglob("*")
                    if f.is_file()
                ]
            else:
                pairs = [(source, target)]

            for source_file, file_target in pairs:
                # Symlinks and missing targets have no content to compare
                if file_target.is_symlink() or not file_target.is_file():
                    continue
                try:
                    if link_manager.is_template_file(source_file):
                        wanted = template_engine.render_file(source_file, variables)
                    else:
                        wanted = source_file.read_text()
                    current = file_target.read_text()
                except (DotmanError, OSError, UnicodeDecodeError) as e:
                    console.print(f"[red]Cannot diff {file_target}:[/red] {e}")
                    continue

                lines = list(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        wanted.splitlines(keepends=True),
                        fromfile=str(file_target),
                        tofile=str(source_file),
                    )
                )
                if lines:
                    found = True
                    console.print(Syntax("".join(lines), "diff", theme="ansi_dark"))

    if not found:
        console.print("[green]No differences.[/green]")
        return
    raise typer.Exit(1)
