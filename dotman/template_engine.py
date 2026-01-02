"""Jinja2 template engine for Dotman."""

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateError, UndefinedError

from dotman.exceptions import TemplateRenderError

# Pattern to detect Jinja2 template syntax
TEMPLATE_PATTERN = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}")


class TemplateEngine:
    """Jinja2 template rendering engine."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get or create the Jinja2 environment."""
        if self._env is None:
            if self.template_dir:
                self._env = Environment(
                    loader=FileSystemLoader(str(self.template_dir)),
                    keep_trailing_newline=True,
                    autoescape=False,
                )
            else:
                self._env = Environment(
                    keep_trailing_newline=True,
                    autoescape=False,
                )
        return self._env

    def is_template(self, path: Path) -> bool:
        """Check if a file is a template by looking for Jinja2 syntax."""
        try:
            content = path.read_text()
            return bool(TEMPLATE_PATTERN.search(content))
        except (OSError, UnicodeDecodeError):
            return False

    def render_file(
        self, source: Path, variables: dict[str, Any], output: Path | None = None
    ) -> str:
        """Render a template file with the given variables."""
        try:
            content = source.read_text()
            rendered = self.render_string(content, variables)

            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered)

            return rendered
        except OSError as e:
            raise TemplateRenderError(f"Error reading template {source}: {e}") from e

    def render_string(self, content: str, variables: dict[str, Any]) -> str:
        """Render a template string with the given variables."""
        try:
            template = self.env.from_string(content)
            return template.render(**variables)
        except UndefinedError as e:
            raise TemplateRenderError(f"Undefined variable in template: {e}") from e
        except TemplateError as e:
            raise TemplateRenderError(f"Template error: {e}") from e

    def get_template_variables(self, path: Path) -> set[str]:
        """Extract variable names used in a template."""
        try:
            content = path.read_text()
            return self.get_string_variables(content)
        except OSError:
            return set()

    def get_string_variables(self, content: str) -> set[str]:
        """Extract variable names from a template string."""
        from jinja2 import meta

        try:
            ast = self.env.parse(content)
            return meta.find_undeclared_variables(ast)
        except TemplateError:
            return set()
