"""Jinja2 template engine for Dotman."""

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateError, UndefinedError

from dotman.exceptions import TemplateRenderError

TEMPLATE_PATTERN = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}")


@dataclass
class RenderedTemplate:
    """Represents a rendered template with cache metadata."""

    content: str
    source_mtime: float
    variables_hash: str
    rendered_at: float


class TemplateEngine:
    """Jinja2 template rendering engine with cache state detection."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir
        self._env: Environment | None = None
        self._cache: dict[Path, RenderedTemplate] = {}

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

    def _get_variables_hash(self, variables: dict[str, Any]) -> str:
        """Create a hash of variables for cache key."""
        var_str = repr(sorted(variables.items()))
        return hashlib.md5(var_str.encode()).hexdigest()

    def _get_source_mtime(self, source: Path) -> float:
        """Get the modification time of the source file."""
        try:
            return source.stat().st_mtime
        except OSError:
            return 0.0

    def get_cache_status(
        self, source: Path, variables: dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if a cached render is valid for the given source and variables.

        Args:
            source: Path to the template source file
            variables: Template variables used for rendering

        Returns:
            Tuple of (is_valid: bool, reason: str)
        """
        if not source.exists():
            return False, "source_not_exists"

        if source not in self._cache:
            return False, "not_cached"

        cached = self._cache[source]
        current_mtime = self._get_source_mtime(source)
        variables_hash = self._get_variables_hash(variables)

        if current_mtime > cached.source_mtime:
            return False, "source_modified"

        if variables_hash != cached.variables_hash:
            return False, "variables_changed"

        return True, "valid"

    def invalidate_cache(self, source: Path | None = None) -> int:
        """Invalidate the cache for a source or all sources.

        Args:
            source: Optional specific source file to invalidate.
                   If None, invalidates all cached entries.

        Returns:
            Number of cache entries invalidated
        """
        if source is not None:
            if source in self._cache:
                del self._cache[source]
                return 1
            return 0

        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cached_content(self, source: Path) -> str | None:
        """Get the cached rendered content for a source if available and valid.

        Args:
            source: Path to the template source file

        Returns:
            Cached content if valid, None otherwise
        """
        if source in self._cache:
            return self._cache[source].content
        return None

    def render_file(
        self, source: Path, variables: dict[str, Any], output: Path | None = None
    ) -> str:
        """Render a template file with the given variables.

        Uses cached render if source and variables haven't changed.
        """
        try:
            is_valid, _ = self.get_cache_status(source, variables)

            if is_valid and output is None:
                cached = self.get_cached_content(source)
                if cached is not None:
                    return cached

            content = source.read_text()
            rendered = self.render_string(content, variables)

            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered)

            if not is_valid or output is None:
                self._cache[source] = RenderedTemplate(
                    content=rendered,
                    source_mtime=self._get_source_mtime(source),
                    variables_hash=self._get_variables_hash(variables),
                    rendered_at=time.monotonic(),
                )

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
