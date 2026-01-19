"""Status and list commands for dotman CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from dotman.commands import app, console, get_config
from dotman.link_manager import LinkManager, LinkStatus
from dotman.template_engine import TemplateEngine


@app.command()
def status(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to check (default: all enabled)"),
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
) -> None:
    """Show status of deployed dotfiles."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    packages_to_check = packages or config.get_enabled_packages()

    if not packages_to_check:
        console.print("[yellow]No packages configured.[/yellow]")
        return

    link_manager = LinkManager(config.backup_dir)

    table = Table(title="Dotman Status")
    table.add_column("Package", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Status", style="white")

    status_styles = {
        LinkStatus.LINKED: "[green]Linked[/green]",
        LinkStatus.MISSING: "[red]Missing source[/red]",
        LinkStatus.BROKEN: "[yellow]Broken link[/yellow]",
        LinkStatus.CONFLICT: "[red]Conflict[/red]",
        LinkStatus.NOT_DEPLOYED: "[dim]Not deployed[/dim]",
        LinkStatus.MODIFIED: "[yellow]Modified[/yellow]",
        LinkStatus.SYNCED: "[green]Synced[/green]",
    }

    for pkg_name in packages_to_check:
        pkg = config.get_package(pkg_name)
        if not pkg:
            table.add_row(pkg_name, "-", "[yellow]Not found[/yellow]")
            continue

        for file_mapping in pkg.files:
            source = config.dotfiles_dir / file_mapping.source
            target = Path(file_mapping.target).expanduser()

            if source.is_dir():
                for source_file in source.rglob("*"):
                    if source_file.is_file():
                        relative_path = source_file.relative_to(source)
                        file_target = target / relative_path

                        display_target = file_target
                        if link_manager.is_template_file(source_file):
                            display_target = link_manager.get_template_target(
                                file_target
                            )

                        variables = None
                        template_engine_instance = None
                        if link_manager.is_template_file(source_file):
                            variables = config.get_merged_variables(pkg_name)
                            template_engine_instance = TemplateEngine()

                        link_status = link_manager.get_link_status(
                            source_file,
                            file_target,
                            template_engine_instance,
                            variables,
                        )

                        status_str = status_styles.get(
                            link_status, str(link_status.value)
                        )
                        table.add_row(pkg_name, str(display_target), status_str)
            else:
                display_target = target
                if link_manager.is_template_file(source):
                    display_target = link_manager.get_template_target(target)

                variables = None
                template_engine_instance = None
                if link_manager.is_template_file(source):
                    variables = config.get_merged_variables(pkg_name)
                    template_engine_instance = TemplateEngine()

                link_status = link_manager.get_link_status(
                    source, target, template_engine_instance, variables
                )
                status_str = status_styles.get(link_status, str(link_status.value))
                table.add_row(pkg_name, str(display_target), status_str)

    console.print(table)


@app.command(name="list")
def list_packages(
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
) -> None:
    """List all available packages."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    enabled = set(config.get_enabled_packages())
    all_packages = config.global_config.packages

    if not all_packages:
        console.print("[yellow]No packages defined in global config.[/yellow]")
        return

    table = Table(title="Available Packages")
    table.add_column("Package", style="cyan")
    table.add_column("Enabled", style="white")
    table.add_column("Files", style="white")
    table.add_column("Dependencies", style="white")

    for name, pkg in all_packages.items():
        is_enabled = "[green]Yes[/green]" if name in enabled else "[dim]No[/dim]"
        files_count = str(len(pkg.files))
        deps = ", ".join(pkg.depends) if pkg.depends else "-"

        table.add_row(name, is_enabled, files_count, deps)

    console.print(table)
