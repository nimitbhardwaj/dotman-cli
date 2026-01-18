"""Hook execution for shell commands."""

import subprocess
from pathlib import Path
from typing import Any

from dotman.exceptions import HookExecutionError
from dotman.template_engine import TemplateEngine


class HookExecutor:
    """Executes shell command hooks for packages."""

    def __init__(
        self,
        dry_run: bool = False,
        cwd: Path | None = None,
        template_engine: TemplateEngine | None = None,
    ):
        """Initialize the hook executor.

        Args:
            dry_run: If True, commands are not actually executed.
            cwd: Working directory for command execution. Defaults to current directory.
            template_engine: Template engine for rendering command templates.
        """
        self.dry_run = dry_run
        self.cwd = cwd or Path.cwd()
        self.template_engine = template_engine or TemplateEngine()

    def execute_hook(
        self,
        command: str,
        package_name: str,
        hook_type: str,
        variables: dict[str, Any] | None = None,
        dotfiles_dir: Path | None = None,
        target_dir: Path | None = None,
    ) -> None:
        """Execute a single shell command hook.

        Args:
            command: The shell command to execute.
            package_name: Name of the package this hook belongs to.
            hook_type: Type of hook (pre_deploy or post_deploy).
            variables: Optional variables for template rendering in the command.
            dotfiles_dir: Path to the dotfiles directory.
            target_dir: Path to the target directory for the package.

        Raises:
            HookExecutionError: If the command fails to execute.
        """
        if self.dry_run:
            return

        try:
            expanded_command = self._render_template(
                command,
                package_name,
                variables,
                dotfiles_dir,
                target_dir,
            )
            subprocess.run(
                expanded_command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise HookExecutionError(
                f"Hook '{command}' failed in package '{package_name}' ({hook_type}):"
                f" exit code {e.returncode}\nstdout: {e.stdout}\nstderr: {e.stderr}"
            ) from e
        except Exception as e:
            raise HookExecutionError(
                f"Hook '{command}' failed in package '{package_name}' ({hook_type}):"
                f" {e}"
            ) from e

    def execute_hooks(
        self,
        commands: list[str],
        package_name: str,
        hook_type: str,
        variables: dict[str, Any] | None = None,
        dotfiles_dir: Path | None = None,
        target_dir: Path | None = None,
    ) -> None:
        """Execute a list of shell command hooks.

        Args:
            commands: List of shell commands to execute.
            package_name: Name of the package these hooks belong to.
            hook_type: Type of hooks (pre_deploy or post_deploy).
            variables: Optional variables for template rendering in commands.
            dotfiles_dir: Path to the dotfiles directory.
            target_dir: Path to the target directory for the package.
        """
        for command in commands:
            self.execute_hook(
                command,
                package_name,
                hook_type,
                variables,
                dotfiles_dir,
                target_dir,
            )

    def _render_template(
        self,
        command: str,
        package_name: str,
        variables: dict[str, Any] | None = None,
        dotfiles_dir: Path | None = None,
        target_dir: Path | None = None,
    ) -> str:
        """Render a command template with Jinja2 and special variables.

        Args:
            command: The command string with optional Jinja2 template syntax.
            package_name: Name of the package.
            variables: Dictionary of variables to substitute.
            dotfiles_dir: Path to the dotfiles directory.
            target_dir: Path to the target directory for the package.

        Returns:
            The command with templates rendered.
        """
        context: dict[str, Any] = {}

        if variables:
            context.update(variables)

        context["package_name"] = package_name

        if dotfiles_dir:
            context["dotfiles_dir"] = str(dotfiles_dir)

        if target_dir:
            context["target_dir"] = str(target_dir)

        return self.template_engine.render_string(command, context)
