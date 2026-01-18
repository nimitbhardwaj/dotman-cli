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
    last_accessed_at: float = 0.0
    access_count: int = 0


@dataclass
class CacheStatistics:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    renders: int = 0
    invalidations: int = 0
    total_accesses: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        total = self.hits + self.misses
        return self.misses / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, int | float]:
        """Convert statistics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "renders": self.renders,
            "invalidations": self.invalidations,
            "total_accesses": self.total_accesses,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
        }


class TemplateEngine:
    """Jinja2 template rendering engine with cache state detection."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir
        self._env: Environment | None = None
        self._cache: dict[Path, RenderedTemplate] = {}
        self._stats = CacheStatistics()
        self._cache_hits: dict[Path, int] = {}

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
            self._stats.misses += 1
            self._stats.total_accesses += 1
            return False, "source_not_exists"

        if source not in self._cache:
            self._stats.misses += 1
            self._stats.total_accesses += 1
            return False, "not_cached"

        cached = self._cache[source]
        current_mtime = self._get_source_mtime(source)
        variables_hash = self._get_variables_hash(variables)

        if current_mtime > cached.source_mtime:
            self._stats.misses += 1
            self._stats.total_accesses += 1
            return False, "source_modified"

        if variables_hash != cached.variables_hash:
            self._stats.misses += 1
            self._stats.total_accesses += 1
            return False, "variables_changed"

        self._stats.hits += 1
        self._stats.total_accesses += 1
        cached.last_accessed_at = time.monotonic()
        cached.access_count += 1
        if source not in self._cache_hits:
            self._cache_hits[source] = 0
        self._cache_hits[source] += 1

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
                if source in self._cache_hits:
                    del self._cache_hits[source]
                self._stats.invalidations += 1
                return 1
            return 0

        count = len(self._cache)
        self._cache.clear()
        self._cache_hits.clear()
        self._stats.invalidations += count
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

    def get_cache_statistics(self) -> CacheStatistics:
        """Get current cache performance statistics.

        Returns:
            CacheStatistics object with current stats
        """
        return CacheStatistics(
            hits=self._stats.hits,
            misses=self._stats.misses,
            renders=self._stats.renders,
            invalidations=self._stats.invalidations,
            total_accesses=self._stats.total_accesses,
        )

    def get_cache_info(self) -> dict[str, Any]:
        """Get comprehensive cache information.

        Returns:
            Dictionary with cache statistics and metadata
        """
        stats = self.get_cache_statistics()
        cache_entries = []
        for source, template in self._cache.items():
            cache_entries.append(
                {
                    "source": str(source),
                    "rendered_at": template.rendered_at,
                    "last_accessed_at": template.last_accessed_at,
                    "access_count": template.access_count,
                    "source_mtime": template.source_mtime,
                }
            )

        return {
            "statistics": stats.to_dict(),
            "cache_size": len(self._cache),
            "entries": cache_entries,
        }

    def get_most_accessed_templates(self, limit: int = 5) -> list[tuple[Path, int]]:
        """Get the most accessed templates in the cache.

        Args:
            limit: Maximum number of templates to return

        Returns:
            List of (source_path, access_count) tuples sorted by access count
        """
        sorted_entries = sorted(
            self._cache_hits.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_entries[:limit]

    def get_oldest_templates(self, limit: int = 5) -> list[tuple[Path, float]]:
        """Get the oldest rendered templates in the cache.

        Args:
            limit: Maximum number of templates to return

        Returns:
            List of (source_path, rendered_at) tuples sorted by render time
        """
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].rendered_at)
        return [
            (source, template.rendered_at)
            for source, template in sorted_entries[:limit]
        ]

    def clear_statistics(self) -> None:
        """Reset all cache statistics to zero."""
        self._stats = CacheStatistics()

    def invalidate_cache_by_pattern(
        self, pattern: str, base_path: Path | None = None
    ) -> int:
        """Invalidate cache entries matching a glob pattern.

        Args:
            pattern: Glob pattern to match source paths
            base_path: Optional base path for pattern matching

        Returns:
            Number of cache entries invalidated
        """
        import fnmatch

        count = 0
        paths_to_remove = []

        for source in self._cache.keys():
            source_str = str(source)
            if base_path:
                try:
                    source_str = str(source.relative_to(base_path))
                except ValueError:
                    pass

            # Try both the full path and just the filename
            if (
                fnmatch.fnmatch(source_str, pattern)
                or fnmatch.fnmatch(source.name, pattern)
                or fnmatch.fnmatch(source_str, f"*{pattern}*")
                or fnmatch.fnmatch(source.name, f"*{pattern}*")
            ):
                paths_to_remove.append(source)

        for source in paths_to_remove:
            if source in self._cache:
                del self._cache[source]
                if source in self._cache_hits:
                    del self._cache_hits[source]
                count += 1

        self._stats.invalidations += count
        return count

    def invalidate_cache_by_directory(self, directory: Path) -> int:
        """Invalidate all cache entries within a directory.

        Args:
            directory: Directory path to invalidate cache for

        Returns:
            Number of cache entries invalidated
        """
        directory = directory.resolve()
        count = 0
        paths_to_remove = []

        for source in self._cache.keys():
            try:
                if source.resolve().is_relative_to(directory):
                    paths_to_remove.append(source)
            except (ValueError, OSError):
                pass

        for source in paths_to_remove:
            if source in self._cache:
                del self._cache[source]
                if source in self._cache_hits:
                    del self._cache_hits[source]
                count += 1

        self._stats.invalidations += count
        return count

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
            self._stats.renders += 1

            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered)

            if not is_valid or output is None:
                self._cache[source] = RenderedTemplate(
                    content=rendered,
                    source_mtime=self._get_source_mtime(source),
                    variables_hash=self._get_variables_hash(variables),
                    rendered_at=time.monotonic(),
                    last_accessed_at=time.monotonic(),
                    access_count=1,
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
