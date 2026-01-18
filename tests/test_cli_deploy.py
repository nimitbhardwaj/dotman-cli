"""Integration tests for the deploy CLI command."""

import yaml

from dotman.cli import app


class TestDeployCommand:
    """Integration tests for dotman deploy command."""

    def test_deploy_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test deploy fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["deploy"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_deploy_no_packages(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test deploy with no packages enabled shows appropriate message."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 0
        assert "no packages to deploy" in result.output.lower()

    def test_deploy_specific_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test deploying a specific package by name."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["deploy", "vim"])

        assert result.exit_code == 0
        assert (
            "vim" in result.output.lower()
            or "deploying package" in result.output.lower()
        )

    def test_deploy_all_enabled_packages(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test deploying all enabled packages."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 0
        assert (
            "bash" in result.output.lower()
            or "deploying package" in result.output.lower()
        )

    def test_deploy_nonexistent_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test deploying a package that doesn't exist in config."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["deploy", "nonexistent"])

        assert result.exit_code == 1
        assert (
            "not found" in result.output.lower()
            or "dependency" in result.output.lower()
        )

    def test_deploy_dry_run(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test deploy with --dry-run flag shows actions without making changes."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["deploy", "--dry-run"])

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()

        dotfiles_dir = home_dir / ".bashrc"
        assert not dotfiles_dir.exists(), "File should not be created in dry run mode"

    def test_deploy_force_flag(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test deploy with --force flag overwrites existing files."""
        monkeypatch.chdir(repo_with_source_files)

        bashrc_path = home_dir / ".bashrc"
        bashrc_path.parent.mkdir(parents=True, exist_ok=True)
        bashrc_path.write_text("# Existing content\n")

        result = runner.invoke(app, ["deploy", "--force"])

        assert result.exit_code == 0
        assert bashrc_path.exists(), "File should exist after force deploy"
        assert bashrc_path.is_symlink(), "File should be a symlink"

    def test_deploy_missing_source_file(
        self, runner, repo_with_missing_source, env_with_home, monkeypatch, home_dir
    ):
        """Test deploy handles missing source files gracefully."""
        monkeypatch.chdir(repo_with_missing_source)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 0
        assert "error" in result.output.lower() or "missing" in result.output.lower()

    def test_deploy_circular_dependency(
        self, runner, repo_with_circular_dependency, env_with_home, monkeypatch
    ):
        """Test deploy fails with circular dependency error."""
        monkeypatch.chdir(repo_with_circular_dependency)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 1
        assert result.exception is not None
        assert (
            "circular" in str(result.exception).lower()
            or "dependency" in str(result.exception).lower()
        )

    def test_deploy_missing_dependency(
        self, runner, temp_repo, env_with_home, monkeypatch
    ):
        """Test deploy fails when a dependency is not defined."""
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
                "pkg_a": {
                    "depends": ["pkg_b"],
                    "files": [{"source": "a/file", "target": "~/.a"}],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["pkg_a"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 1
        assert "dependency" in result.output.lower()

    def test_deploy_disabled_dependency(
        self, runner, temp_repo, env_with_home, monkeypatch
    ):
        """Test deploy fails when a dependency is not enabled."""
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
                "pkg_a": {
                    "depends": ["pkg_b"],
                    "files": [{"source": "a/file", "target": "~/.a"}],
                    "variables": {},
                },
                "pkg_b": {
                    "depends": [],
                    "files": [{"source": "b/file", "target": "~/.b"}],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["pkg_a"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 1
        assert "dependency" in result.output.lower()

    def test_deploy_creates_symlinks(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test deploy creates correct symlinks."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["deploy", "bash"])

        assert result.exit_code == 0

        bashrc_link = home_dir / ".bashrc"
        assert bashrc_link.exists(), "Symlink should be created"
        assert bashrc_link.is_symlink(), "Target should be a symlink"
        assert bashrc_link.resolve() == repo_with_source_files / "bash/.bashrc"

    def test_deploy_complete_message(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test deploy shows complete message at the end."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 0
        assert "complete" in result.output.lower()

    def test_deploy_with_config_dir_option(
        self, runner, repo_with_source_files, env_with_home, tmp_path, monkeypatch
    ):
        """Test deploy with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = repo_with_source_files

        result = runner.invoke(app, ["deploy", "--config-dir", str(config_dir), "bash"])

        assert result.exit_code == 0

    def test_deploy_preserves_existing_symlink(
        self, runner, repo_with_source_files, env_with_home, monkeypatch, home_dir
    ):
        """Test deploy preserves existing correct symlink without error."""
        monkeypatch.chdir(repo_with_source_files)

        bashrc_link = home_dir / ".bashrc"
        bashrc_link.parent.mkdir(parents=True, exist_ok=True)
        bashrc_link.symlink_to(repo_with_source_files / "bash/.bashrc")

        result = runner.invoke(app, ["deploy", "bash"])

        assert result.exit_code == 0
        assert bashrc_link.is_symlink()

    def test_deploy_with_template_files(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test deploy handles template files (.j2 extension)."""
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

        result = runner.invoke(app, ["deploy"])

        assert result.exit_code == 0
        assert (
            "rendered" in result.output.lower() or "template" in result.output.lower()
        )

        bashrc_tmpl = home_dir / ".bashrc_tmpl"
        assert bashrc_tmpl.exists(), "Rendered template should exist"
        assert not bashrc_tmpl.is_symlink(), "Rendered template should not be symlink"
        assert "testuser" in bashrc_tmpl.read_text()
