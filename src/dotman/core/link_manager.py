"""Symlink management for Dotman."""

import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotman.core.exceptions import (
    LinkExistsError,
    LinkTargetMissingError,
    TemplateRenderError,
)

if TYPE_CHECKING:
    from dotman.core.template_engine import TemplateEngine


class LinkStatus(Enum):
    """Status of a symlink or template file."""

    LINKED = "linked"  # Correctly linked
    MISSING = "missing"  # Link target doesn't exist
    BROKEN = "broken"  # Link exists but points to wrong location
    CONFLICT = "conflict"  # File exists but is not a symlink
    NOT_DEPLOYED = "not_deployed"  # Link doesn't exist
    MODIFIED = "modified"  # Template-generated file was modified
    SYNCED = "synced"  # Template-generated file matches source


@dataclass
class LinkResult:
    """Result of a link operation."""

    source: Path
    target: Path
    status: LinkStatus
    message: str = ""
    backed_up: Path | None = None


class LinkManager:
    """Manages symlinks for dotfiles."""

    def __init__(self, backup_dir: Path | None = None):
        self.backup_dir = backup_dir or Path.home() / ".dotman" / "backups"

    def is_template_file(self, path: Path) -> bool:
        """Check if a file is a template based on .j2 extension."""
        return path.suffix == ".j2"

    def get_template_target(self, source: Path) -> Path:
        """Get the target path for a template file (strips .j2 extension)."""
        return source.with_suffix("")

    def normalize_content(self, content: str) -> str:
        """Normalize content by stripping leading/trailing whitespace."""
        return content.strip()

    def compare_content(
        self, source: Path, target: Path, variables: dict[str, Any], template_engine
    ) -> tuple[bool, str]:
        """Compare rendered template content with actual file content.

        Args:
            source: Path to the template source file
            target: Path to the target file
            variables: Template variables
            template_engine: TemplateEngine instance

        Returns:
            Tuple of (is_synced: bool, rendered_content: str)
        """
        try:
            # Render the template
            rendered = template_engine.render_file(source, variables)

            # Normalize both contents for comparison
            normalized_rendered = self.normalize_content(rendered)

            if target.exists():
                actual_content = target.read_text()
                normalized_actual = self.normalize_content(actual_content)
                is_synced = normalized_rendered == normalized_actual
            else:
                is_synced = False

            return is_synced, rendered
        except Exception:
            # If rendering fails, return False (not synced)
            return False, ""

    def get_link_status(
        self,
        source: Path,
        target: Path,
        template_engine=None,
        variables: dict[str, Any] | None = None,
    ) -> LinkStatus:
        """Check the status of a symlink or template file.

        Args:
            source: Path to the source file
            target: Path to the target file
            template_engine: Optional TemplateEngine instance for template comparison
            variables: Optional template variables for rendering comparison
        """
        if not source.exists():
            return LinkStatus.MISSING

        # Check if source is a template file
        if self.is_template_file(source):
            # For template files, we check if the rendered file exists
            if not target.exists():
                return LinkStatus.NOT_DEPLOYED

            # If template_engine is provided, compare content
            if template_engine is not None:
                is_synced, _ = self.compare_content(
                    source, target, variables or {}, template_engine
                )
                return LinkStatus.MODIFIED if not is_synced else LinkStatus.SYNCED

            # If no template_engine, assume synced if file exists
            return LinkStatus.SYNCED

        if not target.exists() and not target.is_symlink():
            return LinkStatus.NOT_DEPLOYED

        if target.is_symlink():
            if target.resolve() == source.resolve():
                return LinkStatus.LINKED
            else:
                return LinkStatus.BROKEN

        return LinkStatus.CONFLICT

    def create_link(
        self,
        source: Path,
        target: Path,
        force: bool = False,
        dry_run: bool = False,
        template_engine: "TemplateEngine | None" = None,
        variables: dict[str, Any] | None = None,
    ) -> list[LinkResult]:
        """Create symlinks from target to source.

        If source is a directory, recursively symlinks all individual files.
        This prevents generated files (like node_modules) from polluting dotfiles.
        """
        source = source.expanduser().resolve()
        target = target.expanduser()

        # If source is a directory, recursively symlink individual files
        if source.is_dir():
            return self._create_links_recursive(
                source, target, force, dry_run, template_engine, variables
            )

        # Single file symlink
        return [
            self._create_single_link(
                source, target, force, dry_run, template_engine, variables
            )
        ]

    def derive_target(
        self, source_file: Path, source_dir: Path, target_dir: Path
    ) -> Path:
        """Map a file inside a source directory to its target path.

        Templates found inside directories drop their .j2 suffix.
        """
        target_file = target_dir / source_file.relative_to(source_dir)
        if self.is_template_file(source_file):
            return self.get_template_target(target_file)
        return target_file

    def _create_links_recursive(
        self,
        source_dir: Path,
        target_dir: Path,
        force: bool = False,
        dry_run: bool = False,
        template_engine: "TemplateEngine | None" = None,
        variables: dict[str, Any] | None = None,
    ) -> list[LinkResult]:
        """Recursively create symlinks for all files in a directory."""
        results = []

        for source_file in source_dir.rglob("*"):
            if source_file.is_file():
                # Calculate relative path and target location
                target_file = self.derive_target(source_file, source_dir, target_dir)

                result = self._create_single_link(
                    source_file, target_file, force, dry_run, template_engine, variables
                )
                results.append(result)

        return results

    def _create_single_link(
        self,
        source: Path,
        target: Path,
        force: bool = False,
        dry_run: bool = False,
        template_engine: "TemplateEngine | None" = None,
        variables: dict[str, Any] | None = None,
    ) -> LinkResult:
        """Create a single symlink from target to source."""
        # Handle template files by rendering them (no symlink for templates)
        if template_engine and self.is_template_file(source):
            try:
                if dry_run:
                    return LinkResult(
                        source=source,
                        target=target,
                        status=LinkStatus.LINKED,
                        message=f"Would render template: {target}",
                    )
                rendered = template_engine.render_file(source, variables or {})
                backed_up = None
                if target.is_symlink():
                    # Writing would go through the link into the repo
                    target.unlink()
                elif target.exists() and target.read_text() != rendered:
                    backed_up = self._backup_file(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rendered)
                return LinkResult(
                    source=source,
                    target=target,
                    status=LinkStatus.LINKED,
                    message=f"Rendered template: {target}",
                    backed_up=backed_up,
                )
            except (OSError, TemplateRenderError) as e:
                raise TemplateRenderError(
                    f"Failed to render template {source}: {e}"
                ) from e

        status = self.get_link_status(source, target)

        if status == LinkStatus.MISSING:
            raise LinkTargetMissingError(f"Source file does not exist: {source}")

        if status == LinkStatus.LINKED:
            return LinkResult(
                source=source,
                target=target,
                status=LinkStatus.LINKED,
                message="Already linked correctly",
            )

        if status == LinkStatus.CONFLICT:
            if not force:
                raise LinkExistsError(
                    f"Target exists and is not a symlink:"
                    f" {target}. Use --force to backup and replace."
                )
            if not dry_run:
                backed_up = self._backup_file(target)
                return self._create_symlink(source, target, backed_up)
            return LinkResult(
                source=source,
                target=target,
                status=LinkStatus.LINKED,
                message=f"Would backup {target} and create link",
            )

        if status == LinkStatus.BROKEN:
            if not dry_run:
                target.unlink()
                return self._create_symlink(source, target)
            return LinkResult(
                source=source,
                target=target,
                status=LinkStatus.LINKED,
                message="Would fix broken symlink",
            )

        if not dry_run:
            return self._create_symlink(source, target)

        return LinkResult(
            source=source,
            target=target,
            status=LinkStatus.LINKED,
            message=f"Would create link: {target} -> {source}",
        )

    def _create_symlink(
        self, source: Path, target: Path, backed_up: Path | None = None
    ) -> LinkResult:
        """Actually create the symlink."""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
        return LinkResult(
            source=source,
            target=target,
            status=LinkStatus.LINKED,
            message=f"Created link: {target} -> {source}",
            backed_up=backed_up,
        )

    def _backup_file(self, path: Path) -> Path:
        """Backup a file before replacing it."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}.{timestamp}.{uuid.uuid4().hex[:6]}"
        backup_path = self.backup_dir / backup_name
        shutil.move(str(path), str(backup_path))
        return backup_path

    def remove_link(
        self, source: Path, target: Path, dry_run: bool = False
    ) -> list[LinkResult]:
        """Remove symlinks.

        If source is a directory, recursively removes all individual file symlinks.
        """
        source = source.expanduser().resolve()
        target = target.expanduser()

        # If source is a directory, recursively remove individual file links
        if source.is_dir():
            return self._remove_links_recursive(source, target, dry_run)

        return [self._remove_single_link(source, target, dry_run)]

    def _remove_links_recursive(
        self, source_dir: Path, target_dir: Path, dry_run: bool = False
    ) -> list[LinkResult]:
        """Recursively remove symlinks for all files in a directory."""
        results = []

        for source_file in source_dir.rglob("*"):
            if source_file.is_file():
                target_file = self.derive_target(source_file, source_dir, target_dir)

                result = self._remove_single_link(source_file, target_file, dry_run)
                results.append(result)

        return results

    def _remove_single_link(
        self, source: Path, target: Path, dry_run: bool = False
    ) -> LinkResult:
        """Remove a single symlink."""
        status = self.get_link_status(source, target)

        if status == LinkStatus.NOT_DEPLOYED:
            return LinkResult(
                source=source,
                target=target,
                status=LinkStatus.NOT_DEPLOYED,
                message="Link does not exist",
            )

        if status == LinkStatus.CONFLICT:
            return LinkResult(
                source=source,
                target=target,
                status=LinkStatus.CONFLICT,
                message="Target exists but is not a symlink, skipping",
            )

        if status in (LinkStatus.LINKED, LinkStatus.BROKEN):
            if not dry_run:
                target.unlink()
                return LinkResult(
                    source=source,
                    target=target,
                    status=LinkStatus.NOT_DEPLOYED,
                    message=f"Removed link: {target}",
                )
            return LinkResult(
                source=source,
                target=target,
                status=LinkStatus.NOT_DEPLOYED,
                message=f"Would remove link: {target}",
            )

        return LinkResult(
            source=source,
            target=target,
            status=status,
            message=f"Cannot remove: {status.value}",
        )
