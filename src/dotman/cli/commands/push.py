"""Push command for dotman CLI."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from dotman.commands import app, console, get_config
from dotman.exceptions import NothingToCommitError, RemotePushError
from dotman.remote import RemoteManager


@app.command()
def push(
    remote: Annotated[
        str | None,
        typer.Argument(help="Remote name (default: origin)"),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch to push"),
    ] = None,
    set_upstream: Annotated[
        bool,
        typer.Option("--set-upstream", "-u", help="Set remote tracking branch"),
    ] = False,
    stage_only: Annotated[
        bool,
        typer.Option("--stage-only", "-s", help="Stage and commit without pushing"),
    ] = False,
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", "-c", help="The path of config directory"),
    ] = None,
    repo_name: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Repository name"),
    ] = None,
) -> None:
    """Push changes to the remote repository.

    Examples:
        dotman push
        dotman push origin
        dotman push origin main
        dotman push --set-upstream origin develop
        dotman push --repo work
        dotman push --stage-only
    """
    config = get_config(config_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    remote_manager = RemoteManager(config.repo_dir)

    if not remote_manager.is_git_repo():
        console.print("[red]This is not a git repository.[/red]")
        raise typer.Exit(1)

    remote_name = remote or "origin"
    push_branch = branch

    if push_branch is None:
        push_branch = remote_manager.get_current_branch()
        console.print(f"[cyan]Using current branch: {push_branch}[/cyan]")

    try:
        remote_url = remote_manager.get_remote_url(remote_name)

        has_changes = (
            remote_manager.has_staged_changes() or remote_manager.has_unstaged_changes()
        )

        if not has_changes:
            console.print("[yellow]No changes to commit.[/yellow]")
            raise typer.Exit(0)

        console.print("[cyan]Staging all changes...[/cyan]")
        remote_manager.stage_all()

        now = datetime.now(UTC)
        tz_offset = now.astimezone().strftime("%z")
        commit_message = (
            f"dotman update: {now.strftime('%Y-%m-%d %H:%M:%S')} {tz_offset}"
        )

        console.print(f"[cyan]Committing with message: {commit_message}[/cyan]")
        try:
            remote_manager.commit(commit_message)
        except NothingToCommitError:
            console.print("[yellow]No changes to commit.[/yellow]")
            raise typer.Exit(0)

        if stage_only:
            console.print("[green]Changes staged and committed.[/green]")
            return

        console.print(f"[cyan]Pushing to: {remote_name} ({remote_url})[/cyan]")
        console.print(f"  Branch: {push_branch}")

        remote_manager.push(
            remote=remote_name,
            branch=push_branch,
            set_upstream=set_upstream,
        )

        console.print("[green]Successfully pushed to remote![/green]")
    except NothingToCommitError:
        console.print("[yellow]No changes to commit.[/yellow]")
        raise typer.Exit(0)
    except RemotePushError as e:
        console.print(f"[red]Changes staged and committed but push failed:[/red] {e}")
        raise typer.Exit(1)
