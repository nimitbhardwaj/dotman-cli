"""Integration tests for the absorb CLI command."""

import yaml

from dotman.cli import app


class TestAbsorbCommand:
    """Integration tests for dotman absorb command."""

    def test_absorb_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test absorb fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["absorb"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_absorb_dry_run_does_not_modify_files(
        self, runner, deployed_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test absorb --dry-run shows what would be done without making changes."""
        monkeypatch.chdir(deployed_repo)

        result = runner.invoke(app, ["absorb", "--dry-run"])

        assert result.exit_code == 0

        dotfiles_dir = deployed_repo / "bash"
        assert not (dotfiles_dir / ".bashrc_original").exists()
        bashrc_link = home_dir / ".bashrc"
        assert bashrc_link.is_symlink()
        assert bashrc_link.resolve() == deployed_repo / "bash" / ".bashrc"

    def test_absorb_specific_package(
        self, runner, deployed_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test absorbing a specific package."""
        monkeypatch.chdir(deployed_repo)

        result = runner.invoke(app, ["absorb", "bash"])

        assert result.exit_code == 0
        assert "complete" in result.output.lower()
        assert (home_dir / ".bashrc").is_symlink()

    def test_absorb_moves_file_and_creates_symlink(
        self, runner, deployed_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test absorb moves file to source and creates symlink."""
        monkeypatch.chdir(deployed_repo)

        result = runner.invoke(app, ["absorb"])

        assert result.exit_code == 0
        assert (
            "absorbed" in result.output.lower() or "complete" in result.output.lower()
        )

        home_bashrc = home_dir / ".bashrc"
        assert home_bashrc.is_symlink()

        source_bashrc = deployed_repo / "bash" / ".bashrc"
        assert source_bashrc.exists()

    def test_absorb_skips_nonexistent_source(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test absorb skips files where source doesn't exist."""
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
                "bash": {
                    "depends": [],
                    "files": [{"source": "bash/.bashrc", "target": "~/.bashrc"}],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["bash"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        bashrc_in_home = home_dir / ".bashrc"
        bashrc_in_home.parent.mkdir(parents=True, exist_ok=True)
        bashrc_in_home.write_text("# content\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["absorb"])

        assert result.exit_code == 0
        assert (
            "does not exist" in result.output.lower() or "skip" in result.output.lower()
        )

    def test_absorb_skips_nonexistent_target(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test absorb skips files where target doesn't exist."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["absorb"])

        assert result.exit_code == 0
        assert (
            "does not exist" in result.output.lower() or "skip" in result.output.lower()
        )

    def test_absorb_handles_directory_targets(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test absorb handles directory targets correctly."""
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
                    "files": [{"source": "config/dir", "target": "~/.config_dir"}],
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

        config_home = home_dir / ".config_dir"
        config_home.mkdir(parents=True)
        (config_home / "file1").write_text("# modified file1\n")
        (config_home / "file2").write_text("# modified file2\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["absorb"])

        assert result.exit_code == 0

    def test_absorb_with_template_file_in_source(
        self, runner, temp_repo, env_with_home, monkeypatch, home_dir
    ):
        """Test absorb skips files when corresponding .j2 template exists in source."""
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
                "bash": {
                    "depends": [],
                    "files": [{"source": "bash/.bashrc", "target": "~/.bashrc"}],
                    "variables": {},
                },
            },
        }

        local_config = {
            "packages": ["bash"],
            "variables": {},
            "file_overrides": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(local_config_path, "w") as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

        bash_dir = repo_dir / "bash"
        bash_dir.mkdir()
        (bash_dir / ".bashrc").write_text("# existing\n")
        (bash_dir / ".bashrc.j2").write_text("# template {{ user }}\n")

        bashrc_in_home = home_dir / ".bashrc"
        bashrc_in_home.parent.mkdir(parents=True, exist_ok=True)
        bashrc_in_home.write_text("# modified\n")

        monkeypatch.chdir(repo_dir)

        result = runner.invoke(app, ["absorb"])

        assert result.exit_code == 0
