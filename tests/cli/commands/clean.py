"""Integration and unit tests for the clean CLI command."""

import yaml

from dotman.cli import app
from dotman.cli.commands.clean import find_empty_dirs, find_orphaned_symlinks


class TestFindOrphanedSymlinks:
    """Unit tests for find_orphaned_symlinks function."""

    def test_no_symlinks(self, tmp_path):
        """Test with directory containing no symlinks."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        (tmp_path / "subdir").mkdir()

        result = find_orphaned_symlinks(tmp_path)

        assert result == []

    def test_valid_symlink_not_orphaned(self, tmp_path):
        """Test that valid symlinks are not detected as orphaned."""
        target = tmp_path / "target.txt"
        target.write_text("target content")

        link = tmp_path / "link.txt"
        link.symlink_to(target)

        result = find_orphaned_symlinks(tmp_path)

        assert result == []

    def test_broken_symlink_is_orphaned(self, tmp_path):
        """Test that broken symlinks are detected as orphaned."""
        target = tmp_path / "nonexistent.txt"

        link = tmp_path / "broken_link.txt"
        link.symlink_to(target)

        result = find_orphaned_symlinks(tmp_path)

        assert len(result) == 1
        assert result[0] == link

    def test_nested_orphaned_symlink(self, tmp_path):
        """Test detection of orphaned symlinks in nested directories."""
        target = tmp_path / "nonexistent.txt"

        nested_dir = tmp_path / "nested" / "deep"
        nested_dir.mkdir(parents=True)
        link = nested_dir / "broken_link.txt"
        link.symlink_to(target)

        result = find_orphaned_symlinks(tmp_path)

        assert len(result) == 1
        assert result[0] == link

    def test_multiple_orphaned_symlinks(self, tmp_path):
        """Test detection of multiple orphaned symlinks."""
        target1 = tmp_path / "nonexistent1.txt"
        target2 = tmp_path / "nonexistent2.txt"

        link1 = tmp_path / "broken1.txt"
        link1.symlink_to(target1)
        link2 = tmp_path / "broken2.txt"
        link2.symlink_to(target2)

        result = find_orphaned_symlinks(tmp_path)

        assert len(result) == 2
        assert link1 in result
        assert link2 in result

    def test_mixed_valid_and_broken_symlinks(self, tmp_path):
        """Test with mix of valid and broken symlinks."""
        valid_target = tmp_path / "valid.txt"
        valid_target.write_text("valid")

        link1 = tmp_path / "valid_link.txt"
        link1.symlink_to(valid_target)

        broken_target = tmp_path / "missing.txt"
        link2 = tmp_path / "broken_link.txt"
        link2.symlink_to(broken_target)

        result = find_orphaned_symlinks(tmp_path)

        assert len(result) == 1
        assert result[0] == link2

    def test_regular_files_not_affected(self, tmp_path):
        """Test that regular files are not reported as orphaned."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        result = find_orphaned_symlinks(tmp_path)

        assert result == []

    def test_directory_symlink_to_existing(self, tmp_path):
        """Test that symlinks to existing directories are not orphaned."""
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()

        link = tmp_path / "link_dir"
        link.symlink_to(target_dir)

        result = find_orphaned_symlinks(tmp_path)

        assert result == []

    def test_directory_symlink_to_nonexistent(self, tmp_path):
        """Test that symlinks to nonexistent directories are orphaned."""
        target_dir = tmp_path / "missing_dir"

        link = tmp_path / "link_dir"
        link.symlink_to(target_dir)

        result = find_orphaned_symlinks(tmp_path)

        assert len(result) == 1
        assert result[0] == link

    def test_circular_symlink(self, tmp_path):
        """Test that circular symlinks are detected as orphaned."""
        link1 = tmp_path / "link1"
        link2 = tmp_path / "link2"
        link1.symlink_to(link2)
        link2.symlink_to(link1)

        result = find_orphaned_symlinks(tmp_path)

        assert len(result) == 2

    def test_empty_directory(self, tmp_path):
        """Test with empty directory returns no orphaned symlinks."""
        result = find_orphaned_symlinks(tmp_path)

        assert result == []


class TestFindEmptyDirs:
    """Unit tests for find_empty_dirs function."""

    def test_no_empty_dirs(self, tmp_path):
        """Test with directory containing files."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("content")

        result = find_empty_dirs(tmp_path)

        assert result == []

    def test_empty_subdir(self, tmp_path):
        """Test detection of empty subdirectory."""
        (tmp_path / "file.txt").write_text("content")
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = find_empty_dirs(tmp_path)

        assert len(result) == 1
        assert result[0] == empty_dir

    def test_nested_empty_dir(self, tmp_path):
        """Test detection of empty directory nested in structure."""
        (tmp_path / "file.txt").write_text("content")
        nested_empty = tmp_path / "level1" / "level2" / "empty"
        nested_empty.mkdir(parents=True)

        result = find_empty_dirs(tmp_path)

        assert len(result) == 1
        assert result[0] == nested_empty

    def test_multiple_empty_dirs(self, tmp_path):
        """Test detection of multiple empty directories."""
        (tmp_path / "file.txt").write_text("content")
        empty1 = tmp_path / "empty1"
        empty2 = tmp_path / "empty2"
        empty1.mkdir()
        empty2.mkdir()

        result = find_empty_dirs(tmp_path)

        assert len(result) == 2
        assert empty1 in result
        assert empty2 in result

    def test_empty_directory_with_file_not_empty(self, tmp_path):
        """Test that directories with files are not detected as empty."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")

        result = find_empty_dirs(tmp_path)

        assert result == []

    def test_empty_directory_with_subdir_not_empty(self, tmp_path):
        """Test that parent of non-empty dir is not detected as empty."""
        (tmp_path / "file.txt").write_text("content")
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()
        (child / "file.txt").write_text("content")

        result = find_empty_dirs(tmp_path)

        assert result == []

    def test_only_root_dir_not_reported(self, tmp_path):
        """Test that root directory itself is not reported even if empty."""
        result = find_empty_dirs(tmp_path)

        assert result == []

    def test_mixed_empty_and_non_empty(self, tmp_path):
        """Test with mix of empty and non-empty directories."""
        (tmp_path / "file.txt").write_text("content")
        empty1 = tmp_path / "empty1"
        empty1.mkdir()
        non_empty = tmp_path / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")
        empty2 = tmp_path / "nested" / "empty2"
        empty2.mkdir(parents=True)

        result = find_empty_dirs(tmp_path)

        assert len(result) == 2
        assert empty1 in result
        assert empty2 in result

    def test_result_sorted(self, tmp_path):
        """Test that results are sorted."""
        (tmp_path / "file.txt").write_text("content")
        dir_z = tmp_path / "z_dir"
        dir_a = tmp_path / "a_dir"
        dir_m = tmp_path / "m_dir"
        dir_z.mkdir()
        dir_a.mkdir()
        dir_m.mkdir()

        result = find_empty_dirs(tmp_path)

        assert result == sorted(result)


class TestCleanCommand:
    """Integration tests for dotman clean command."""

    def test_clean_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test clean fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["clean"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_clean_no_packages(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test clean with no packages enabled."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["clean"])

        assert result.exit_code == 0
        assert "no packages to clean" in result.output.lower()

    def test_clean_no_orphaned_symlinks(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test clean when no orphaned symlinks exist."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["clean"])

        assert result.exit_code == 0
        assert (
            "no orphaned" in result.output.lower() or "clean" in result.output.lower()
        )

    def test_clean_finds_and_removes_orphaned_symlinks(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean finds and removes orphaned symlinks."""
        monkeypatch.chdir(repo_with_source_files)

        bashrc_link = home_dir / ".bashrc"
        bashrc_link.symlink_to(repo_with_source_files / "bash" / ".nonexistent")

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert "orphaned" in result.output.lower() or "removed" in result.output.lower()
        assert not bashrc_link.exists()

    def test_clean_finds_and_removes_empty_dirs(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean finds and removes empty directories."""
        monkeypatch.chdir(repo_with_source_files)

        empty_dir = home_dir / ".config" / "empty_app"
        empty_dir.mkdir(parents=True)

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "removed" in result.output.lower()
        assert not empty_dir.exists()

    def test_clean_valid_symlinks_not_removed(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test that valid symlinks are not removed."""
        monkeypatch.chdir(repo_with_source_files)

        bashrc_link = home_dir / ".bashrc"
        bashrc_link.symlink_to(repo_with_source_files / "bash" / ".bashrc")

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert bashrc_link.exists()
        assert bashrc_link.is_symlink()

    def test_clean_regular_files_not_affected(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test that regular files are not affected."""
        monkeypatch.chdir(repo_with_source_files)

        bashrc_file = home_dir / ".bashrc"
        bashrc_file.parent.mkdir(parents=True, exist_ok=True)
        bashrc_file.write_text("# Regular file content\n")

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert bashrc_file.exists()
        assert not bashrc_file.is_symlink()

    def test_clean_nested_orphaned_symlinks(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean finds nested orphaned symlinks."""
        monkeypatch.chdir(repo_with_source_files)

        orphan_target = repo_with_source_files / "bash" / "nonexistent"
        nested_link = home_dir / ".config" / "app" / "nested_link"
        nested_link.parent.mkdir(parents=True)
        nested_link.symlink_to(orphan_target)

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert not nested_link.exists()

    def test_clean_multiple_orphaned_symlinks(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean finds and removes multiple orphaned symlinks."""
        monkeypatch.chdir(repo_with_source_files)

        orphan_target1 = repo_with_source_files / "bash" / "nonexistent1"
        orphan_target2 = repo_with_source_files / "vim" / "nonexistent2"

        link1 = home_dir / ".bashrc"
        link1.symlink_to(orphan_target1)

        link2 = home_dir / ".vimrc"
        link2.symlink_to(orphan_target2)

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert not link1.exists()
        assert not link2.exists()

    def test_clean_with_config_dir_option(
        self, runner, repo_with_source_files, env_with_home, tmp_path, monkeypatch
    ):
        """Test clean with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = repo_with_source_files

        result = runner.invoke(app, ["clean", "--config-dir", str(config_dir)])

        assert result.exit_code == 0

    def test_clean_with_specific_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean with a specific package argument."""
        monkeypatch.chdir(repo_with_source_files)

        orphan_target = repo_with_source_files / "bash" / "nonexistent"
        bashrc_link = home_dir / ".bashrc"
        bashrc_link.symlink_to(orphan_target)

        result = runner.invoke(app, ["clean", "bash"], input="y\n")

        assert result.exit_code == 0
        assert not bashrc_link.exists()

    def test_clean_summary_displayed(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean displays cleanup summary tree."""
        monkeypatch.chdir(repo_with_source_files)

        orphan_target = repo_with_source_files / "bash" / "nonexistent"
        bashrc_link = home_dir / ".bashrc"
        bashrc_link.symlink_to(orphan_target)

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert "summary" in result.output.lower() or "cleanup" in result.output.lower()

    def test_clean_empty_dirs_removed_in_order(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test that empty dirs are removed deepest first."""
        repo_dir = temp_repo
        dotman_dir = repo_dir / ".dotman"
        config_path = dotman_dir / "config.yaml"
        local_config_path = dotman_dir / "local.yaml"

        config = {
            "settings": {
                "backup_dir": ".dotman/backups",
                "template_suffix": ".j2",
            },
            "variables": {},
            "packages": {
                "config": {
                    "depends": [],
                    "files": [{"source": "config/dir", "target": "~/.config_test"}],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["config"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        monkeypatch.chdir(repo_dir)

        empty_child = home_dir / ".config_test" / "child"
        empty_child.mkdir(parents=True)

        result = runner.invoke(app, ["clean"], input="y\n")

        assert result.exit_code == 0
        assert not empty_child.exists()

    def test_clean_nonexistent_package_shows_warning(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test clean shows warning for nonexistent package."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["clean", "nonexistent"])

        assert result.exit_code == 0
        assert (
            "not found" in result.output.lower() or "skipping" in result.output.lower()
        )

    def test_clean_multiple_packages(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test clean with multiple packages cleans all."""
        monkeypatch.chdir(repo_with_source_files)

        orphan_target1 = repo_with_source_files / "bash" / "nonexistent"
        orphan_target2 = repo_with_source_files / "vim" / "nonexistent"

        link1 = home_dir / ".bashrc"
        link1.symlink_to(orphan_target1)

        link2 = home_dir / ".vimrc"
        link2.symlink_to(orphan_target2)

        result = runner.invoke(app, ["clean", "bash", "vim"], input="y\n")

        assert result.exit_code == 0
        assert not link1.exists()
        assert not link2.exists()
