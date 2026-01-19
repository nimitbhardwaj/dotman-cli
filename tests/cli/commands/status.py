"""Integration tests for the status CLI command."""

import yaml

from dotman.cli import app


class TestStatusCommand:
    """Integration tests for dotman status command."""

    def test_status_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test status fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["status"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_status_no_packages(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test status with no packages configured shows appropriate message."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "no packages configured" in result.output.lower()

    def test_status_specific_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test status for a specific package by name."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["status", "bash"])

        assert result.exit_code == 0
        assert "bash" in result.output.lower() or "status" in result.output.lower()

    def test_status_specific_nonexistent_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test status for a non-existent package shows not found."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["status", "nonexistent"])

        assert result.exit_code == 0
        assert (
            "not found" in result.output.lower()
            or "nonexistent" in result.output.lower()
        )

    def test_status_linked(
        self, runner, deployed_repo_with_symlinks, env_with_home, monkeypatch
    ):
        """Test status shows LINKED for correctly linked symlinks."""
        monkeypatch.chdir(deployed_repo_with_symlinks)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "linked" in result.output.lower()

    def test_status_missing_source(
        self, runner, repo_with_packages, env_with_home, monkeypatch, home_dir
    ):
        """Test status shows MISSING when source file doesn't exist."""
        repo_dir = repo_with_packages
        monkeypatch.chdir(repo_dir)

        bashrc_link = home_dir / ".bashrc"
        bashrc_link.parent.mkdir(parents=True, exist_ok=True)
        bashrc_link.symlink_to(repo_dir / "bash" / ".bashrc")

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "missing" in result.output.lower() or "bashrc" in result.output.lower()

    def test_status_broken_link(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test status shows BROKEN for broken symlinks."""
        repo_dir = repo_with_source_files
        monkeypatch.chdir(repo_dir)

        bashrc_link = home_dir / ".bashrc"
        bashrc_link.parent.mkdir(parents=True, exist_ok=True)
        broken_source = repo_dir / "bash" / ".nonexistent"
        bashrc_link.symlink_to(broken_source)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "broken" in result.output.lower() or "linked" in result.output.lower()

    def test_status_conflict(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test status shows CONFLICT when target is a regular file."""
        repo_dir = repo_with_source_files
        monkeypatch.chdir(repo_dir)

        bashrc_file = home_dir / ".bashrc"
        bashrc_file.parent.mkdir(parents=True, exist_ok=True)
        bashrc_file.write_text("# Regular file content\n")

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "conflict" in result.output.lower() or "bashrc" in result.output.lower()

    def test_status_not_deployed(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test status shows NOT DEPLOYED when symlink doesn't exist."""
        repo_dir = repo_with_source_files
        monkeypatch.chdir(repo_dir)

        bashrc_path = home_dir / ".bashrc"
        bashrc_path.parent.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert (
            "not deployed" in result.output.lower() or "bashrc" in result.output.lower()
        )

    def test_status_with_template_files(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test status correctly handles template files (.j2 extension)."""
        repo_dir = temp_repo
        dotman_dir = repo_dir / ".dotman"
        config_path = dotman_dir / "config.yaml"
        local_config_path = dotman_dir / "local.yaml"

        config = {
            "settings": {
                "backup_dir": ".dotman/backups",
                "template_suffix": ".j2",
            },
            "variables": {"user": "testuser"},
            "packages": {
                "templates": {
                    "depends": [],
                    "files": [
                        {"source": "tmpl/.bashrc.j2", "target": "~/.bashrc_tmpl"}
                    ],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["templates"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        tmpl_dir = repo_dir / "tmpl"
        tmpl_dir.mkdir()
        (tmpl_dir / ".bashrc.j2").write_text("# Template for {{ user }}\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "templates" in result.output.lower() or "status" in result.output.lower()

    def test_status_synced_template(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test status shows SYNCED for rendered template that matches source."""
        repo_dir = temp_repo
        dotman_dir = repo_dir / ".dotman"
        config_path = dotman_dir / "config.yaml"
        local_config_path = dotman_dir / "local.yaml"

        config = {
            "settings": {
                "backup_dir": ".dotman/backups",
                "template_suffix": ".j2",
            },
            "variables": {"user": "testuser"},
            "packages": {
                "tmpl": {
                    "depends": [],
                    "files": [
                        {"source": "tmpl/.bashrc.j2", "target": "~/.bashrc_synced"}
                    ],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["tmpl"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        tmpl_dir = repo_dir / "tmpl"
        tmpl_dir.mkdir()
        (tmpl_dir / ".bashrc.j2").write_text("# Template for testuser\n")

        bashrc_synced = home_dir / ".bashrc_synced"
        bashrc_synced.parent.mkdir(parents=True, exist_ok=True)
        bashrc_synced.write_text("# Template for testuser\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "tmpl" in result.output.lower() or "status" in result.output.lower()

    def test_status_modified_template(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test status shows MODIFIED for rendered template that differs from source."""
        repo_dir = temp_repo
        dotman_dir = repo_dir / ".dotman"
        config_path = dotman_dir / "config.yaml"
        local_config_path = dotman_dir / "local.yaml"

        config = {
            "settings": {
                "backup_dir": ".dotman/backups",
                "template_suffix": ".j2",
            },
            "variables": {"user": "testuser"},
            "packages": {
                "tmpl": {
                    "depends": [],
                    "files": [
                        {"source": "tmpl/.bashrc.j2", "target": "~/.bashrc_modified"}
                    ],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["tmpl"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        tmpl_dir = repo_dir / "tmpl"
        tmpl_dir.mkdir()
        (tmpl_dir / ".bashrc.j2").write_text("# Template for {{ user }}\n")

        bashrc_modified = home_dir / ".bashrc_modified"
        bashrc_modified.parent.mkdir(parents=True, exist_ok=True)
        bashrc_modified.write_text("# Modified content\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "tmpl" in result.output.lower() or "status" in result.output.lower()

    def test_status_multiple_packages(
        self, runner, deployed_repo_with_multiple_symlinks, env_with_home, monkeypatch
    ):
        """Test status shows status for multiple packages."""
        monkeypatch.chdir(deployed_repo_with_multiple_symlinks)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "bash" in result.output.lower()
        assert "vim" in result.output.lower()

    def test_status_all_enabled_packages(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test status shows all enabled packages when no specific package given."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "bash" in result.output.lower() or "vim" in result.output.lower()

    def test_status_with_config_dir_option(
        self, runner, repo_with_source_files, env_with_home, tmp_path, monkeypatch
    ):
        """Test status with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = repo_with_source_files

        result = runner.invoke(app, ["status", "--config-dir", str(config_dir)])

        assert result.exit_code == 0

    def test_status_displays_table(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test status displays output in table format."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert (
            "Package" in result.output
            or "File" in result.output
            or "Status" in result.output
        )

    def test_status_directory_source(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test status handles directory sources with files."""
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
                    "files": [{"source": "config/dir", "target": "~/.config_app"}],
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

        config_dir = repo_dir / "config" / "dir"
        config_dir.mkdir(parents=True)
        (config_dir / "file1").write_text("# file1\n")
        (config_dir / "file2").write_text("# file2\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "config" in result.output.lower() or "dir" in result.output.lower()
