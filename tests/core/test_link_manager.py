"""Unit tests for the LinkManager class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dotman.core.exceptions import LinkExistsError, LinkTargetMissingError
from dotman.core.link_manager import LinkManager, LinkStatus


class TestLinkManagerInit:
    """Test LinkManager initialization."""

    def test_default_backup_directory(self):
        """Test LinkManager uses default backup directory."""
        manager = LinkManager()
        expected_backup = Path.home() / ".dotman" / "backups"
        assert manager.backup_dir == expected_backup

    def test_custom_backup_directory(self):
        """Test LinkManager accepts custom backup directory."""
        custom_backup = Path("/custom/backups")
        manager = LinkManager(backup_dir=custom_backup)
        assert manager.backup_dir == custom_backup


class TestTemplateFileDetection:
    """Test template file detection functionality."""

    def test_is_template_file_true(self):
        """Test is_template_file returns True for .j2 files."""
        manager = LinkManager()
        path = Path("/some/path/file.j2")
        assert manager.is_template_file(path) is True

    def test_is_template_file_false(self):
        """Test is_template_file returns False for non-.j2 files."""
        manager = LinkManager()
        path = Path("/some/path/file.txt")
        assert manager.is_template_file(path) is False

    def test_is_template_file_empty_suffix(self):
        """Test is_template_file handles files without suffix."""
        manager = LinkManager()
        path = Path("/some/path/config")
        assert manager.is_template_file(path) is False

    def test_get_template_target(self):
        """Test get_template_target strips .j2 extension."""
        manager = LinkManager()
        source = Path("/some/path/file.j2")
        target = manager.get_template_target(source)
        assert target == Path("/some/path/file")

    def test_get_template_target_no_extension(self):
        """Test get_template_target handles files without extension."""
        manager = LinkManager()
        source = Path("/some/path/config")
        target = manager.get_template_target(source)
        assert target == source  # Should be unchanged


class TestLinkStatus:
    """Test link status detection functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_status_missing_source(self):
        """Test status is MISSING when source doesn't exist."""
        manager = LinkManager()
        source = self.repo_dir / "missing_source"
        target = self.repo_dir / "target"

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.MISSING

    def test_status_not_deployed_regular_file(self):
        """Test status is NOT_DEPLOYED when link doesn't exist."""
        manager = LinkManager()
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.NOT_DEPLOYED

    def test_status_linked_correctly(self):
        """Test status is LINKED when symlink points to correct source."""
        manager = LinkManager()
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.symlink_to(source)

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.LINKED

    def test_status_broken_link(self):
        """Test status is BROKEN when symlink points to wrong location."""
        manager = LinkManager()
        source = self.repo_dir / "source"
        source.touch()
        wrong_source = self.repo_dir / "wrong_source"
        wrong_source.touch()
        target = self.repo_dir / "target"
        target.symlink_to(wrong_source)

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.BROKEN

    def test_status_conflict(self):
        """Test status is CONFLICT when file exists but is not symlink."""
        manager = LinkManager()
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.write_text("regular file content")

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.CONFLICT

    def test_status_template_not_deployed(self):
        """Test status is NOT_DEPLOYED for template files not rendered."""
        manager = LinkManager()
        source = self.repo_dir / "template.j2"
        source.write_text("template content")
        target = self.repo_dir / "target"

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.NOT_DEPLOYED

    def test_status_template_deployed(self):
        """Test status is SYNCED for template files that exist."""
        manager = LinkManager()
        source = self.repo_dir / "template.j2"
        source.write_text("template content")
        target = self.repo_dir / "target"
        target.write_text("rendered content")

        status = manager.get_link_status(source, target)
        assert status == LinkStatus.SYNCED


class TestContentNormalization:
    """Test content normalization functionality."""

    def test_normalize_content_strips_whitespace(self):
        """Test normalize_content strips leading and trailing whitespace."""
        manager = LinkManager()
        content = "  hello world  \n\t"
        normalized = manager.normalize_content(content)
        assert normalized == "hello world"

    def test_normalize_content_empty(self):
        """Test normalize_content handles empty content."""
        manager = LinkManager()
        normalized = manager.normalize_content("")
        assert normalized == ""

    def test_normalize_content_no_whitespace(self):
        """Test normalize_content preserves content without whitespace changes."""
        manager = LinkManager()
        content = "hello world"
        normalized = manager.normalize_content(content)
        assert normalized == "hello world"


class TestLinkCreation:
    """Test symlink creation functionality."""

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

    def test_create_link_success(self):
        """Test creating a symlink successfully."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"

        results = manager.create_link(source, target)
        assert len(results) == 1
        assert results[0].status == LinkStatus.LINKED
        assert target.is_symlink()
        # Use resolve() on both paths to handle macOS /private symlinks
        assert target.resolve() == source.resolve()

    def test_create_link_missing_source_raises_error(self):
        """Test creating link with missing source raises error."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "missing_source"
        target = self.repo_dir / "target"

        with pytest.raises(LinkTargetMissingError):
            manager.create_link(source, target)

    def test_create_link_already_linked(self):
        """Test creating link when already linked returns success."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.symlink_to(source)

        results = manager.create_link(source, target)
        assert len(results) == 1
        assert results[0].status == LinkStatus.LINKED
        assert results[0].message == "Already linked correctly"

    def test_create_link_conflict_without_force(self):
        """Test creating link with conflict without force raises error."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.write_text("existing content")

        with pytest.raises(LinkExistsError):
            manager.create_link(source, target, force=False)

    def test_create_link_conflict_with_force(self):
        """Test creating link with conflict and force succeeds."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.write_text("source content")
        target = self.repo_dir / "target"
        target.write_text("existing content")

        results = manager.create_link(source, target, force=True)
        assert len(results) == 1
        assert results[0].status == LinkStatus.LINKED
        assert target.is_symlink()
        # Use resolve() on both paths to handle macOS /private symlinks
        assert target.resolve() == source.resolve()

    def test_create_link_broken_link(self):
        """Test creating link with broken existing link fixes it."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        wrong_source = self.repo_dir / "wrong_source"
        wrong_source.touch()
        target = self.repo_dir / "target"
        target.symlink_to(wrong_source)

        results = manager.create_link(source, target)
        assert len(results) == 1
        assert results[0].status == LinkStatus.LINKED
        assert target.is_symlink()
        # Use resolve() on both paths to handle macOS /private symlinks
        assert target.resolve() == source.resolve()

    def test_create_link_dry_run(self):
        """Test dry run doesn't create actual link."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"

        results = manager.create_link(source, target, dry_run=True)
        assert len(results) == 1
        assert results[0].status == LinkStatus.LINKED
        assert not target.exists()  # Should not actually create link

    def test_create_link_dry_run_conflict(self):
        """Test dry run with conflict shows message without creating."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.write_text("existing content")

        results = manager.create_link(source, target, force=True, dry_run=True)
        assert len(results) == 1
        assert results[0].status == LinkStatus.LINKED
        assert "Would backup" in results[0].message
        assert not target.is_symlink()


class TestRecursiveLinkCreation:
    """Test recursive symlink creation for directories."""

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

    def test_create_link_directory(self):
        """Test creating links for all files in a directory."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        results = manager.create_link(source_dir, target_dir)

        assert len(results) == 2
        assert all(r.status == LinkStatus.LINKED for r in results)
        assert (target_dir / "file1.txt").is_symlink()
        assert (target_dir / "file2.txt").is_symlink()

    def test_create_link_directory_preserves_structure(self):
        """Test creating links preserves directory structure."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested content")
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        results = manager.create_link(source_dir, target_dir)

        assert len(results) == 1
        nested_target = target_dir / "subdir" / "nested.txt"
        assert nested_target.is_symlink()

    def test_create_link_directory_ignores_directories(self):
        """Test creating links recursively processes all files."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        results = manager.create_link(source_dir, target_dir)

        # The implementation DOES create links for files in subdirectories
        # This test documents the actual behavior
        assert len(results) == 1
        nested_target = target_dir / "subdir" / "file.txt"
        assert nested_target.is_symlink()


class TestLinkRemoval:
    """Test symlink removal functionality."""

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

    def test_remove_link_success(self):
        """Test removing an existing symlink."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.symlink_to(source)

        results = manager.remove_link(source, target)

        assert len(results) == 1
        assert results[0].status == LinkStatus.NOT_DEPLOYED
        assert not target.exists()

    def test_remove_link_not_deployed(self):
        """Test removing link that doesn't exist returns NOT_DEPLOYED."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"

        results = manager.remove_link(source, target)

        assert len(results) == 1
        assert results[0].status == LinkStatus.NOT_DEPLOYED
        assert results[0].message == "Link does not exist"

    def test_remove_link_conflict(self):
        """Test removing link when target is not symlink."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.write_text("regular file")

        results = manager.remove_link(source, target)

        assert len(results) == 1
        assert results[0].status == LinkStatus.CONFLICT
        assert target.exists()  # Should not delete regular file

    def test_remove_link_dry_run(self):
        """Test dry run doesn't actually remove link."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        target = self.repo_dir / "target"
        target.symlink_to(source)

        results = manager.remove_link(source, target, dry_run=True)

        assert len(results) == 1
        assert results[0].status == LinkStatus.NOT_DEPLOYED
        assert target.exists()  # Should not actually remove


class TestRecursiveLinkRemoval:
    """Test recursive symlink removal for directories."""

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

    def test_remove_link_directory(self):
        """Test removing links for all files in a directory."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()
        (target_dir / "file1.txt").symlink_to(source_dir / "file1.txt")
        (target_dir / "file2.txt").symlink_to(source_dir / "file2.txt")

        results = manager.remove_link(source_dir, target_dir)

        assert len(results) == 2
        assert all(r.status == LinkStatus.NOT_DEPLOYED for r in results)
        assert not (target_dir / "file1.txt").exists()
        assert not (target_dir / "file2.txt").exists()


class TestBackupFunctionality:
    """Test backup functionality."""

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

    def test_backup_file_creates_backup(self):
        """Test backing up a file creates backup with timestamp."""
        manager = LinkManager(backup_dir=self.backup_dir)
        target = self.repo_dir / "target"
        target.write_text("original content")

        backup_path = manager._backup_file(target)

        assert backup_path.exists()
        assert backup_path.read_text() == "original content"
        assert not target.exists()  # Original should be moved

    def test_backup_file_creates_directory(self):
        """Test backup creates backup directory if it doesn't exist."""
        manager = LinkManager(backup_dir=self.repo_dir / "new_backups")
        target = self.repo_dir / "target"
        target.write_text("content")

        backup_path = manager._backup_file(target)

        assert backup_path.parent.exists()
        assert backup_path.exists()

    def test_backup_multiple_files(self):
        """Test backing up multiple files creates separate backups."""
        manager = LinkManager(backup_dir=self.backup_dir)
        target1 = self.repo_dir / "target1"
        target1.write_text("content1")
        target2 = self.repo_dir / "target2"
        target2.write_text("content2")

        backup1 = manager._backup_file(target1)
        backup2 = manager._backup_file(target2)

        assert backup1.exists()
        assert backup2.exists()
        assert backup1.read_text() == "content1"
        assert backup2.read_text() == "content2"
        assert backup1 != backup2  # Different timestamps


class TestContentComparison:
    """Test template content comparison functionality."""

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

    def test_compare_synced_content(self):
        """Test comparing synced template content."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "template.j2"
        source.write_text("Hello {{ name }}!")
        target = self.repo_dir / "target"
        target.write_text("Hello World!")

        template_engine = MagicMock()
        template_engine.render_file.return_value = "Hello World!"

        is_synced, rendered = manager.compare_content(
            source, target, {"name": "World"}, template_engine
        )

        assert is_synced is True
        assert rendered == "Hello World!"

    def test_compare_modified_content(self):
        """Test comparing modified template content."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "template.j2"
        source.write_text("Hello {{ name }}!")
        target = self.repo_dir / "target"
        target.write_text("Hello Modified!")

        template_engine = MagicMock()
        template_engine.render_file.return_value = "Hello World!"

        is_synced, rendered = manager.compare_content(
            source, target, {"name": "World"}, template_engine
        )

        assert is_synced is False

    def test_compare_missing_target(self):
        """Test comparing when target doesn't exist."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "template.j2"
        source.write_text("Hello {{ name }}!")
        target = self.repo_dir / "target"

        template_engine = MagicMock()
        template_engine.render_file.return_value = "Hello World!"

        is_synced, rendered = manager.compare_content(
            source, target, {"name": "World"}, template_engine
        )

        assert is_synced is False

    def test_compare_rendering_error(self):
        """Test comparing when template rendering fails."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "template.j2"
        source.write_text("Hello {{ name }}!")
        target = self.repo_dir / "target"
        target.write_text("Hello World!")

        template_engine = MagicMock()
        template_engine.render_file.side_effect = Exception("Render error")

        is_synced, rendered = manager.compare_content(
            source, target, {"name": "World"}, template_engine
        )

        assert is_synced is False
        assert rendered == ""


class TestEdgeCases:
    """Test edge cases and error handling."""

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

    def test_expanduser_in_paths(self):
        """Test that paths with ~ are expanded to home directory."""
        manager = LinkManager(backup_dir=self.backup_dir)

        # Create source in home directory
        home_source = Path.home() / ".dotman_test_source"
        home_source.touch()

        try:
            # Test with tilde path (should work with expanduser)
            results = manager.create_link(
                Path("~/.dotman_test_source"), Path("~/.dotman_test_target")
            )

            assert len(results) == 1
            assert results[0].status == LinkStatus.LINKED
        finally:
            # Cleanup
            if home_source.exists():
                home_source.unlink()
            target = Path.home() / ".dotman_test_target"
            if target.is_symlink():
                target.unlink()

    def test_symlink_creation_creates_parent_dirs(self):
        """Test symlink creation creates parent directories."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source = self.repo_dir / "source"
        source.touch()
        nested_target = self.repo_dir / "nested" / "deep" / "target"

        results = manager.create_link(source, nested_target)

        assert len(results) == 1
        assert nested_target.is_symlink()

    def test_empty_source_directory(self):
        """Test handling empty source directory."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source_dir = self.repo_dir / "empty"
        source_dir.mkdir()
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        results = manager.create_link(source_dir, target_dir)

        assert len(results) == 0  # No files to link

    def test_mixed_files_and_directories_in_source(self):
        """Test handling source with both files and directories."""
        manager = LinkManager(backup_dir=self.backup_dir)
        source_dir = self.repo_dir / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested content")
        target_dir = self.repo_dir / "target"
        target_dir.mkdir()

        results = manager.create_link(source_dir, target_dir)

        # Implementation links all files recursively
        assert len(results) == 2
        assert (target_dir / "file.txt").is_symlink()
        assert (target_dir / "subdir" / "nested.txt").is_symlink()
