"""History and rollback commands for dotman CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from dotman.commands import app, console, get_config
from dotman.history import HistoryManager


@app.command(name="history")
def history(
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
