"""CLI commands for Dotman using Typer."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dotman.config import Config
from dotman.exceptions import (
    DotmanError,
    LinkExistsError,
    LinkTargetMissingError,
    MissingDependencyError,
)
from dotman.link_manager import LinkManager, LinkStatus
from dotman.template_engine import TemplateEngine

app = typer.Typer(
    name="dotman",
    help="A dotfile manager for symlinks and templates.",
    no_args_is_help=True,
)
console = Console()


def get_config() -> Config:
    """Get the configuration instance."""
    return Config()


@app.command()
def init() -> None:
    """Initialize dotman configuration in the current directory.

    Creates a .dotman/ folder with global.yaml and local.yaml configs.
    Run this from your dotfiles repository root.
    """
    config = get_config()

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


@app.command()
def deploy(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to deploy (default: all enabled)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force overwrite existing files"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Show what would be done without doing it"
        ),
    ] = False,
) -> None:
    """Deploy dotfiles by creating symlinks."""
    config = get_config()

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    # Validate dependencies before proceeding
    packages_to_validate = packages or config.get_enabled_packages()
    try:
        config.validate_dependencies(packages_to_validate)
    except MissingDependencyError as e:
        console.print(f"[red]Dependency error:[/red] {e}")
        raise typer.Exit(1)

    packages_to_deploy = packages or config.get_enabled_packages()

    if not packages_to_deploy:
        console.print(
            "[yellow]No packages to deploy. Add packages to local.yaml.[/yellow]"
        )
        return

    link_manager = LinkManager(config.backup_dir)
    template_engine = TemplateEngine(config.dotfiles_dir)

    if dry_run:
        console.print("[cyan]Dry run mode - no changes will be made[/cyan]")

    for pkg_name in packages_to_deploy:
        pkg = config.get_package(pkg_name)
        if not pkg:
            console.print(
                f"[yellow]Package '{pkg_name}' not found"
                f" in global config, skipping.[/yellow]"
            )
            continue

        console.print(f"\n[bold]Deploying package: {pkg_name}[/bold]")
        variables = config.get_merged_variables(pkg_name)

        for file_mapping in pkg.files:
            source = config.dotfiles_dir / file_mapping.source
            target = Path(file_mapping.target).expanduser()

            try:
                # Check if file is a template
                # (either explicitly marked or auto-detected by .j2 extension)
                # Auto-detect templates by .j2 extension
                is_template = link_manager.is_template_file(source)

                if is_template:
                    if not dry_run:
                        template_engine.render_file(source, variables, target)
                        console.print(f"  [green]Rendered:[/green] {target}")
                    else:
                        console.print(f"  [cyan]Would render:[/cyan] {target}")
                else:
                    results = link_manager.create_link(
                        source, target, force, dry_run, template_engine, variables
                    )
                    for result in results:
                        if result.status == LinkStatus.LINKED:
                            if dry_run:
                                console.print(f"  [cyan]{result.message}[/cyan]")
                            else:
                                console.print(
                                    f"  [green]Linked:[/green]"
                                    f" {result.target} -> {result.source}"
                                )
                            if result.backed_up:
                                console.print(
                                    f"    [yellow]Backed"
                                    f" up to:[/yellow] {result.backed_up}"
                                )
            except LinkExistsError as e:
                console.print(f"  [red]Error:[/red] {e}")
            except LinkTargetMissingError as e:
                console.print(f"  [red]Error:[/red] {e}")
            except DotmanError as e:
                console.print(f"  [red]Error:[/red] {e}")

    console.print("\n[green]Deploy complete![/green]")


@app.command()
def undeploy(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to undeploy (default: all enabled)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Show what would be done without doing it"
        ),
    ] = False,
) -> None:
    """Remove deployed dotfile symlinks."""
    config = get_config()

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    # Validate dependencies before proceeding
    packages_to_validate = packages or config.get_enabled_packages()
    try:
        config.validate_dependencies(packages_to_validate)
    except MissingDependencyError as e:
        console.print(f"[red]Dependency error:[/red] {e}")
        raise typer.Exit(1)

    packages_to_undeploy = packages or config.get_enabled_packages()

    if not packages_to_undeploy:
        console.print("[yellow]No packages to undeploy.[/yellow]")
        return

    link_manager = LinkManager(config.backup_dir)

    if dry_run:
        console.print("[cyan]Dry run mode - no changes will be made[/cyan]")

    for pkg_name in packages_to_undeploy:
        pkg = config.get_package(pkg_name)
        if not pkg:
            console.print(f"[yellow]Package '{pkg_name}' not found, skipping.[/yellow]")
            continue

        console.print(f"\n[bold]Undeploying package: {pkg_name}[/bold]")

        for file_mapping in pkg.files:
            source = config.dotfiles_dir / file_mapping.source
            target = Path(file_mapping.target).expanduser()

            results = link_manager.remove_link(source, target, dry_run)

            for result in results:
                if result.status == LinkStatus.NOT_DEPLOYED:
                    if "Removed" in result.message or "Would remove" in result.message:
                        console.print(f"  [green]{result.message}[/green]")
                    else:
                        console.print(f"  [dim]{result.message}[/dim]")
                elif result.status == LinkStatus.CONFLICT:
                    console.print(f"  [yellow]{result.message}[/yellow]")
                else:
                    console.print(f"  {result.message}")

    console.print("\n[green]Undeploy complete![/green]")


@app.command()
def status(
    packages: Annotated[
        list[str] | None,
        typer.Argument(help="Packages to check (default: all enabled)"),
    ] = None,
) -> None:
    """Show status of deployed dotfiles."""
    config = get_config()

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

            # If source is a directory, show status for each file
            if source.is_dir():
                for source_file in source.rglob("*"):
                    if source_file.is_file():
                        relative_path = source_file.relative_to(source)
                        file_target = target / relative_path

                        # For template files, display the rendered target path
                        display_target = file_target
                        if link_manager.is_template_file(source_file):
                            display_target = link_manager.get_template_target(
                                file_target
                            )

                        # Check if template file has been modified
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
                # For single files, display the correct target path
                display_target = target
                if link_manager.is_template_file(source):
                    display_target = link_manager.get_template_target(target)

                # Check if template file for comparison
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
def list_packages() -> None:
    """List all available packages."""
    config = get_config()

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
