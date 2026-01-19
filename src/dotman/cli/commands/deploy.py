"""Deploy and undeploy commands for dotman CLI."""

import uuid
from pathlib import Path
from typing import Annotated

import typer

from dotman.commands import app, console, get_config
from dotman.core.exceptions import (
    DotmanError,
    HookExecutionError,
    LinkExistsError,
    LinkTargetMissingError,
    MissingDependencyError,
)
from dotman.core.link_manager import LinkManager, LinkStatus
from dotman.core.template_engine import TemplateEngine
from dotman.history import DeployedFile, HistoryManager
from dotman.hook_executor import HookExecutor


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
