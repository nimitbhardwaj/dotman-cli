"""CLI commands for Dotman using Typer."""

import os
import re
import signal
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dotman.config import Config, get_repo_manager
from dotman.exceptions import (
    DotmanError,
    HookExecutionError,
    LinkExistsError,
    LinkTargetMissingError,
    MissingDependencyError,
    RepositoryNotFoundError,
)
from dotman.history import DeployedFile, HistoryManager
from dotman.hook_executor import HookExecutor
from dotman.link_manager import LinkManager, LinkStatus
from dotman.template_engine import TemplateEngine
from dotman.watcher import WatchEvent, WatchEventType, create_watcher

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
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", "-c", help="The path of config directory"),
    ] = None,
    backup_dir: Annotated[
        str | None,
        typer.Option("--backup-dir", help="Override backup directory"),
    ] = None,
    template_suffix: Annotated[
        str | None,
        typer.Option("--template-suffix", help="Override template suffix"),
    ] = None,
    repo_name: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Repository name"),
    ] = None,
) -> None:
    """Deploy dotfiles by creating symlinks."""
    config = get_config(config_dir, backup_dir, template_suffix, repo_name)

    if repo_name:
        console.print(f"[cyan]Using repository: {repo_name}[/cyan]")
        console.print(f"  Path: {config.repo_dir}\n")

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    packages_to_validate = packages or config.get_enabled_packages()
    try:
        config.validate_dependencies(packages_to_validate)
    except MissingDependencyError as e:
        console.print(f"[red]Dependency error:[/red] {e}")
        raise typer.Exit(1)

    packages_to_deploy = config.get_packages_in_deployment_order(packages)

    if not packages_to_deploy:
        console.print(
            "[yellow]No packages to deploy. Add packages to local.yaml.[/yellow]"
        )
        return

    link_manager = LinkManager(config.backup_dir)
    template_engine = TemplateEngine(config.dotfiles_dir)
    history_manager = HistoryManager(config.dotman_dir)
    hook_executor = HookExecutor(dry_run=dry_run)

    deployment_id = str(uuid.uuid4())[:8]
    deployed_files: list[DeployedFile] = []

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

        skip_package = False
        if pkg.hooks.pre_deploy:
            for hook_cmd in pkg.hooks.pre_deploy:
                if dry_run:
                    console.print(
                        f"  [cyan]Would run pre-deploy hook:[/cyan] {hook_cmd}"
                    )
                else:
                    console.print(f"  [cyan]Running pre-deploy hook:[/cyan] {hook_cmd}")
                    try:
                        hook_executor.execute_hook(
                            hook_cmd,
                            pkg_name,
                            "pre_deploy",
                            variables,
                            config.dotfiles_dir,
                            None,
                        )
                    except HookExecutionError as e:
                        console.print(f"  [red]Hook failed:[/red] {e}")
                        console.print(
                            f"  [yellow]Skipping package '{pkg_name}'...[/yellow]"
                        )
                        skip_package = True
                        break

        if skip_package:
            continue

        for file_mapping in pkg.files:
            source = config.dotfiles_dir / file_mapping.source
            target = Path(file_mapping.target).expanduser()

            try:
                is_template = link_manager.is_template_file(source)

                if is_template:
                    if not dry_run:
                        template_engine.render_file(source, variables, target)
                        console.print(f"  [green]Rendered:[/green] {target}")
                    else:
                        console.print(f"  [cyan]Would render:[/cyan] {target}")

                    deployed_files.append(
                        DeployedFile(
                            source=str(source),
                            target=str(target),
                            is_template=True,
                        )
                    )
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

                            deployed_files.append(
                                DeployedFile(
                                    source=str(result.source),
                                    target=str(result.target),
                                    is_template=False,
                                    backup_path=str(result.backed_up)
                                    if result.backed_up
                                    else None,
                                )
                            )
            except LinkExistsError as e:
                console.print(f"  [red]Error:[/red] {e}")
            except LinkTargetMissingError as e:
                console.print(f"  [red]Error:[/red] {e}")
            except DotmanError as e:
                console.print(f"  [red]Error:[/red] {e}")

        if pkg.hooks.post_deploy:
            target_dir = None
            if pkg.files:
                first_target = Path(pkg.files[0].target).expanduser()
                target_dir = first_target.parent

            for hook_cmd in pkg.hooks.post_deploy:
                rendered_cmd = hook_executor._render_template(
                    hook_cmd, pkg_name, variables, config.dotfiles_dir, target_dir
                )
                if dry_run:
                    console.print(
                        f"  [cyan]Would run post-deploy hook:[/cyan] {rendered_cmd}"
                    )
                else:
                    console.print(
                        f"  [cyan]Running post-deploy hook:[/cyan] {rendered_cmd}"
                    )
                    try:
                        hook_executor.execute_hook(
                            hook_cmd,
                            pkg_name,
                            "post_deploy",
                            variables,
                            config.dotfiles_dir,
                            target_dir,
                        )
                    except HookExecutionError as e:
                        console.print(f"  [yellow]Hook warning:[/yellow] {e}")

    if deployed_files and not dry_run:
        history_manager.add_deployment(
            deployment_id=deployment_id,
            packages=packages_to_deploy,
            files=deployed_files,
            dry_run=dry_run,
        )
        console.print("\n[green]Deploy complete![/green]")
        console.print(f"[dim]Deployment ID: {deployment_id}[/dim]")
    elif dry_run and deployed_files:
        console.print("\n[cyan]Dry run complete - no history recorded[/cyan]")
    else:
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
    """Remove deployed dotfile symlinks."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

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

    packages_to_undeploy = config.get_packages_in_undeployment_order(packages)

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


@app.command(name="history")
def show_history(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Number of recent deployments to show"),
    ] = 10,
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
    """Show deployment history."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    history_manager = HistoryManager(config.dotman_dir)
    deployments = history_manager.get_deployments(limit=limit)

    if not deployments:
        console.print("[yellow]No deployment history found.[/yellow]")
        return

    table = Table(title="Deployment History")
    table.add_column("ID", style="cyan")
    table.add_column("Timestamp", style="white")
    table.add_column("Packages", style="white")
    table.add_column("Files", style="white")
    table.add_column("Type", style="white")

    for dep in deployments:
        type_str = "Dry Run" if dep.dry_run else "Live"
        packages_str = ", ".join(dep.packages) if dep.packages else "-"
        files_count = str(len(dep.files))

        table.add_row(
            dep.deployment_id,
            dep.timestamp[:19].replace("T", " "),
            packages_str,
            files_count,
            type_str,
        )

    console.print(table)


@app.command(name="rollback")
def rollback(
    deployment_id: Annotated[
        str | None,
        typer.Argument(help="Deployment ID to rollback (default: latest)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Show what would be done without doing it"
        ),
    ] = False,
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
    """Rollback a deployment by restoring from backup and removing symlinks."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    history_manager = HistoryManager(config.dotman_dir)

    deployment = None
    if deployment_id:
        deployment = history_manager.get_deployment(deployment_id)
        if not deployment:
            console.print(f"[red]Deployment '{deployment_id}' not found.[/red]")
            console.print("Use 'dotman history' to see available deployments.")
            raise typer.Exit(1)
    else:
        deployment = history_manager.get_latest_deployment()
        if not deployment:
            console.print("[red]No deployments found in history.[/red]")
            raise typer.Exit(1)

    if deployment.dry_run:
        console.print(
            "[yellow]Cannot rollback a dry-run deployment"
            " (no changes were made).[/yellow]"
        )
        raise typer.Exit(1)

    if dry_run:
        console.print("[cyan]Rollback dry run - no changes will be made[/cyan]")
    else:
        console.print(
            f"[bold]Rolling back deployment: {deployment.deployment_id}[/bold]"
        )

    console.print(f"Packages: {', '.join(deployment.packages)}")
    console.print(f"Files to process: {len(deployment.files)}\n")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for deployed_file in deployment.files:
        target = Path(deployed_file.target)
        backup_path = deployed_file.backup_path

        console.print(f"Processing: {target}")

        if deployed_file.is_template:
            if target.exists():
                if not dry_run:
                    target.unlink()
                    console.print(
                        f"  [green]Removed rendered template: {target}[/green]"
                    )
                else:
                    console.print(
                        f"  [cyan]Would remove rendered template: {target}[/cyan]"
                    )
                success_count += 1
            else:
                console.print(f"  [yellow]Already removed: {target}[/yellow]")
                skipped_count += 1
        else:
            if target.is_symlink() or target.exists():
                if not dry_run:
                    if target.is_symlink():
                        target.unlink()
                    elif target.is_file():
                        target.unlink()
                    console.print(f"  [green]Removed symlink: {target}[/green]")
                else:
                    console.print(f"  [cyan]Would remove symlink: {target}[/cyan]")
                success_count += 1
            else:
                console.print(f"  [yellow]Already removed: {target}[/yellow]")
                skipped_count += 1

            if backup_path and Path(backup_path).exists():
                if not dry_run:
                    if history_manager.restore_from_backup(Path(backup_path), target):
                        console.print(
                            f"  [green]Restored from backup: {backup_path}[/green]"
                        )
                        history_manager.cleanup_backup(Path(backup_path))
                    else:
                        console.print(
                            f"  [red]Failed to restore from backup: {backup_path}[/red]"
                        )
                        fail_count += 1
                else:
                    console.print(
                        f"  [cyan]Would restore from backup: {backup_path}[/cyan]"
                    )
            elif backup_path:
                console.print(f"  [yellow]Backup not found: {backup_path}[/yellow]")

    console.print("\n[bold]Rollback summary:[/bold]")
    console.print(f"  Processed: {success_count}")
    console.print(f"  Skipped: {skipped_count}")
    console.print(f"  Failed: {fail_count}")

    if not dry_run and success_count > 0:
        history_manager.remove_deployment(deployment.deployment_id)
        console.print(
            "\n[green]Rollback complete! Deployment removed from history.[/green]"
        )
    elif dry_run:
        console.print("\n[cyan]Dry run complete - no changes made[/cyan]")
    else:
        console.print("\n[yellow]Rollback complete with some failures.[/yellow]")


@app.command(name="watch")
def watch(
    debounce: Annotated[
        float,
        typer.Option(
            "--debounce",
            "-d",
            help="Seconds to wait after changes before deploying",
        ),
    ] = 1.0,
    once: Annotated[
        bool,
        typer.Option(
            "--once",
            help="Deploy once on start and exit",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Only show deploy output, not file change events",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Show what would be deployed without doing it",
        ),
    ] = False,
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
    """Watch for file changes and deploy automatically."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    packages_to_deploy = config.get_enabled_packages()
    if not packages_to_deploy:
        console.print(
            "[yellow]No packages to deploy. Add packages to local.yaml.[/yellow]"
        )
        raise typer.Exit(1)

    watcher = create_watcher()
    deploy_scheduled: bool = False
    running = True
    initial_deploy_done = False

    def handle_signal(signum, frame):
        nonlocal running
        console.print("\n[yellow]Stopping watcher...[/yellow]")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    def get_dotfiles_paths() -> list[Path]:
        """Get all source paths from configured packages."""
        paths = []
        for pkg_name in packages_to_deploy:
            pkg = config.get_package(pkg_name)
            if pkg:
                for file_mapping in pkg.files:
                    source = config.dotfiles_dir / file_mapping.source
                    if source.exists():
                        paths.append(source)
        return paths

    def schedule_deploy() -> None:
        """Schedule a deploy after debounce period."""
        nonlocal deploy_scheduled
        deploy_scheduled = True

    def should_deploy_event(event: WatchEvent) -> bool:
        """Determine if an event should trigger a deploy."""
        if event.event_type in (WatchEventType.ACCESSED,):
            return False
        return True

    try:
        console.print("[bold]Starting dotman watch...[/bold]")
        console.print(f"  Watching: {config.dotfiles_dir}")
        console.print(f"  Debounce: {debounce}s")
        console.print(f"  Packages: {', '.join(packages_to_deploy)}")
        console.print("\n[dim]Press Ctrl+C to stop watching[/dim]\n")

        dotfiles_paths = get_dotfiles_paths()
        for path in dotfiles_paths:
            if path.is_dir():
                watcher.add_path(path, recursive=True)
            else:
                watcher.add_path(path)

        if not initial_deploy_done:
            if dry_run:
                console.print("[cyan]Running initial dry-run deploy...[/cyan]\n")
            else:
                console.print("[cyan]Running initial deploy...[/cyan]\n")
            initial_deploy_done = True

            deploy(
                packages=None,
                force=False,
                dry_run=dry_run,
                config_dir=config_dir,
                backup_dir=backup_dir,
                template_suffix=None,
            )

        if once:
            console.print(
                "[green]Initial deploy complete (--once specified, exiting)[/green]"
            )
            return

        deploy_scheduled = False
        last_change_time: float | None = None
        pending_changes: set[Path] = set()

        while running:
            try:
                event = next(watcher.events(timeout=0.5))

                if not quiet:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    console.print(
                        f"[dim][{timestamp}][/dim] Detected: "
                        f"[cyan]{event.event_type.value}[/cyan] "
                        f"{event.path}"
                    )

                if should_deploy_event(event):
                    last_change_time = time.monotonic()
                    pending_changes.add(event.path)
                    if not deploy_scheduled:
                        deploy_scheduled = True

            except StopIteration:
                pass
            except Exception as e:
                console.print(f"[red]Error watching files: {e}[/red]")
                break

            if deploy_scheduled and last_change_time is not None:
                time_since_change = time.monotonic() - last_change_time
                if time_since_change >= debounce:
                    if not quiet and pending_changes:
                        changed_files = ", ".join(
                            str(p.relative_to(config.dotfiles_dir))
                            for p in list(pending_changes)[:5]
                        )
                        if len(pending_changes) > 5:
                            changed_files += f" ... (+{len(pending_changes) - 5} more)"
                        console.print(
                            f"\n[cyan]Deploying changes "
                            f"({len(pending_changes)} files): {changed_files}[/cyan]\n"
                        )
                    else:
                        console.print("\n[cyan]Change detected - deploying...[/cyan]\n")

                    deploy(
                        packages=None,
                        force=False,
                        dry_run=dry_run,
                        config_dir=config_dir,
                        backup_dir=backup_dir,
                        template_suffix=None,
                    )

                    deploy_scheduled = False
                    last_change_time = None
                    pending_changes.clear()

    finally:
        watcher.close()
        console.print("\n[green]Watcher stopped.[/green]")


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
