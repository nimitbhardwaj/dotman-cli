"""Doctor command for checking required executables."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from dotman.cli_utils import app, console, get_config
from dotman.core.exceptions import MissingDependencyError
from dotman.services import DoctorCheckResult, DoctorCommandResult, ExecutableChecker


@app.command(name="doctor")
def doctor(
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
    """Check if required executables are present in PATH."""
    config = get_config(config_dir, backup_dir, repo_name=repo_name)

    if not config.is_initialized():
        console.print("[red]Dotman is not initialized. Run 'dotman init' first.[/red]")
        raise typer.Exit(1)

    try:
        packages_to_check = config.get_all_packages_with_dependencies(packages)
    except MissingDependencyError as e:
        console.print(f"[red]Dependency error:[/red] {e}")
        raise typer.Exit(1)

    if not packages_to_check:
        console.print("[yellow]No packages to check.[/yellow]")
        return

    checker = ExecutableChecker()
    all_results: list[DoctorCommandResult] = []

    for pkg_name in packages_to_check:
        pkg = config.get_package(pkg_name)
        if not pkg:
            continue

        pkg_result = DoctorCommandResult(package_name=pkg_name)
        if pkg.doctor is None or not pkg.doctor.executables:
            all_results.append(pkg_result)
            continue

        for executable in pkg.doctor.executables:
            found, path = checker.find_executable(executable.name)
            check_result = DoctorCheckResult(
                package_name=pkg_name,
                executable_name=executable.name,
                found=found,
                path=path,
                severity=executable.severity,
            )
            pkg_result.checks.append(check_result)

        pkg_result.summary = pkg_result.compute_summary()
        all_results.append(pkg_result)

    table = Table(title="Doctor Check Results")
    table.add_column("Package", style="cyan")
    table.add_column("Executable", style="white")
    table.add_column("Status", style="white")
    table.add_column("Severity", style="white")
    table.add_column("Path", style="dim")

    for pkg_result in all_results:
        table.add_section()
        table.add_row(
            f"[bold]{pkg_result.package_name}[/bold]",
            "",
            "",
            "",
            "",
        )
        if not pkg_result.checks:
            table.add_row(
                "",
                "[dim]No executable requirements[/dim]",
                "",
                "",
                "",
            )
        else:
            for check in pkg_result.checks:
                if check.found:
                    status = "[green]✓ Found[/green]"
                else:
                    status = "[red]✗ Missing[/red]"

                if check.severity == "error":
                    severity = "[red]error[/red]"
                else:
                    severity = "[yellow]warning[/yellow]"

                path_str = check.path if check.path else "Not in PATH"
                table.add_row(
                    "",
                    check.executable_name,
                    status,
                    severity,
                    path_str,
                )

    console.print(table)

    total_errors = sum(r.summary.get("errors", 0) for r in all_results)
    total_warnings = sum(r.summary.get("warnings", 0) for r in all_results)
    total_passed = sum(r.summary.get("passed", 0) for r in all_results)

    console.print(
        f"\nSummary: [red]{total_errors} errors[/red],"
        f" [yellow]{total_warnings} warnings[/yellow],"
        f" [green]{total_passed} passed[/green]"
    )

    if total_errors > 0:
        raise typer.Exit(1)
