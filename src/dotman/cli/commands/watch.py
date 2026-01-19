"""Watch command for dotman CLI."""

import signal
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from dotman.cli_utils import app, console, get_config
from dotman.managers.watcher import WatchEvent, WatchEventType, create_watcher


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
    from dotman.cli.commands.deploy import deploy as deploy_cmd

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

            deploy_cmd(
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

                    deploy_cmd(
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
