"""Test template rendering within directories."""

import tempfile
from pathlib import Path

import pytest

from dotman.link_manager import LinkManager
from dotman.template_engine import TemplateEngine


class TestTemplateRenderingInDirectories:
    """Test that template files inside directories are rendered correctly."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)
        self.backup_dir = self.repo_dir / "backups"
        self.backup_dir.mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_template_file_in_directory_is_rendered(self):
        """Test that .j2 files inside directories are rendered."""
        manager = LinkManager(backup_dir=self.backup_dir)
        template_engine = TemplateEngine()

        # Create source directory with a template file
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        template_file = source_dir / "config.j2"
        template_file.write_text("Hello {{ name }}!")

        # Create target directory
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        # Create link (should render the template)
        variables = {"name": "World"}
        results = manager.create_link(
            source_dir,
            target_dir,
            template_engine=template_engine,  # type: ignore
            variables=variables,  # type: ignore
        )

        # Should have rendered the template
        assert len(results) == 1
        rendered_file = target_dir / "config"
        assert rendered_file.exists()
        assert rendered_file.read_text() == "Hello World!"

    def test_template_file_with_variables(self):
        """Test template rendering with multiple variables."""
        manager = LinkManager(backup_dir=self.backup_dir)
        template_engine = TemplateEngine()

        # Create source directory with a template file
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        template_file = source_dir / "settings.j2"
        template_file.write_text("""
# {{ title }}
email = {{ email }}
editor = {{ editor }}
""")

        # Create target directory
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        # Create link with variables
        variables = {
            "title": "My Config",
            "email": "user@example.com",
            "editor": "vim",
        }
        results = manager.create_link(
            source_dir, target_dir, template_engine=template_engine, variables=variables
        )

        # Should have rendered the template
        rendered_file = target_dir / "settings"
        assert rendered_file.exists()
        content = rendered_file.read_text()
        assert "# My Config" in content
        assert "email = user@example.com" in content
        assert "editor = vim" in content

    def test_mixed_templates_and_regular_files(self):
        """Test handling of both template and regular files in same directory."""
        manager = LinkManager(backup_dir=self.backup_dir)
        template_engine = TemplateEngine()

        # Create source directory with both template and regular files
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()

        # Template file
        template_file = source_dir / "template.j2"
        template_file.write_text("Value: {{ value }}")

        # Regular file
        regular_file = source_dir / "regular.txt"
        regular_file.write_text("Regular content")

        # Create target directory
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        # Create links
        results = manager.create_link(
            source_dir,
            target_dir,
            template_engine=template_engine,
            variables={"value": "test"},
        )

        # Should have 2 results (1 template, 1 regular)
        assert len(results) == 2

        # Check template was rendered
        rendered_file = target_dir / "template"
        assert rendered_file.exists()
        assert rendered_file.read_text() == "Value: test"

        # Check regular file was symlinked
        regular_symlink = target_dir / "regular.txt"
        assert regular_symlink.is_symlink()

    def test_dry_run_does_not_create_files(self):
        """Test that dry run doesn't create actual files."""
        manager = LinkManager(backup_dir=self.backup_dir)
        template_engine = TemplateEngine()

        # Create source directory with a template file
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        template_file = source_dir / "config.j2"
        template_file.write_text("Hello {{ name }}!")

        # Create target directory
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        # Create link in dry run mode
        results = manager.create_link(
            source_dir,
            target_dir,
            dry_run=True,
            template_engine=template_engine,
            variables={"name": "World"},
        )

        # Should not create actual files
        rendered_file = target_dir / "config"
        assert not rendered_file.exists()

        # But should show correct message
        assert len(results) == 1
        assert "Would render template" in results[0].message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
