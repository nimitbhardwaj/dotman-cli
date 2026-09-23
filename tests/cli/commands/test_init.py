"""Integration tests for the init CLI command."""

import pytest
import yaml

from dotman.cli import app


@pytest.fixture
def clean_env(tmp_path, monkeypatch):
    """Set up environment with cleared DOTMAN_CONFIG_DIR."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
    return tmp_path


class TestInitCommand:
    """Integration tests for dotman init command."""

    def test_init_creates_dotman_directory(self, runner, clean_env, monkeypatch):
        """Test init creates .dotman directory."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        dotman_dir = clean_env / ".dotman"
        assert dotman_dir.exists(), ".dotman directory should be created"
        assert dotman_dir.is_dir(), ".dotman should be a directory"

    def test_init_creates_config_yaml(self, runner, clean_env, monkeypatch):
        """Test init creates config.yaml file."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        config_path = clean_env / ".dotman" / "config.yaml"
        assert config_path.exists(), "config.yaml should be created"

    def test_init_creates_local_yaml(self, runner, clean_env, monkeypatch):
        """Test init creates local.yaml file."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        local_config_path = clean_env / ".dotman" / "local.yaml"
        assert local_config_path.exists(), "local.yaml should be created"

    def test_init_creates_valid_config(self, runner, clean_env, monkeypatch):
        """Test init creates valid YAML config files."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        config_path = clean_env / ".dotman" / "config.yaml"
        local_config_path = clean_env / ".dotman" / "local.yaml"

        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert "settings" in config
        assert "packages" in config
        assert config["settings"]["backup_dir"] == ".dotman/backups"

        with open(local_config_path) as f:
            local_config = yaml.safe_load(f)
        assert "packages" in local_config
        assert local_config["packages"] == []

    def test_init_does_not_overwrite_existing_config(
        self, runner, clean_env, monkeypatch
    ):
        """Test init does not overwrite existing config.yaml."""
        original_content = "custom: content\n"
        (clean_env / ".dotman").mkdir()
        (clean_env / ".dotman" / "config.yaml").write_text(original_content)

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        config_content = (clean_env / ".dotman" / "config.yaml").read_text()
        assert config_content == original_content, (
            "Existing config.yaml should not be overwritten"
        )

    def test_init_does_not_overwrite_existing_local_config(
        self, runner, clean_env, monkeypatch
    ):
        """Test init does not overwrite existing local.yaml."""
        original_content = "custom_local: content\n"
        (clean_env / ".dotman").mkdir()
        (clean_env / ".dotman" / "local.yaml").write_text(original_content)

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        local_config_content = (clean_env / ".dotman" / "local.yaml").read_text()
        assert local_config_content == original_content, (
            "Existing local.yaml should not be overwritten"
        )

    def test_init_shows_already_initialized_message(
        self, runner, clean_env, monkeypatch
    ):
        """Test init shows already-initialized message when already initialized."""
        result1 = runner.invoke(app, ["init"])
        assert result1.exit_code == 0

        result2 = runner.invoke(app, ["init"])

        assert result2.exit_code == 0
        assert "already initialized" in result2.output.lower()

    def test_init_shows_repo_directory_in_message(self, runner, clean_env, monkeypatch):
        """Test init shows repository directory in output."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert str(clean_env) in result.output or "repo" in result.output.lower()

    def test_init_shows_config_directory_in_message(
        self, runner, clean_env, monkeypatch
    ):
        """Test init shows config directory in output."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert ".dotman" in result.output

    def test_init_success_message(self, runner, clean_env, monkeypatch):
        """Test init shows success message on first initialization."""
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (
            "success" in result.output.lower() or "initialized" in result.output.lower()
        )

    def test_init_with_existing_dotman_dir_but_missing_config(
        self, runner, clean_env, monkeypatch
    ):
        """Test init works when .dotman dir exists but config files are missing."""
        (clean_env / ".dotman").mkdir()

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (clean_env / ".dotman" / "config.yaml").exists()
        assert (clean_env / ".dotman" / "local.yaml").exists()

    def test_init_with_existing_dotman_shows_already_initialized(
        self, runner, clean_env, monkeypatch
    ):
        """Test init shows already-initialized when .dotman exists with config.yaml."""
        (clean_env / ".dotman").mkdir()
        (clean_env / ".dotman" / "config.yaml").write_text("existing: config\n")

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "already initialized" in result.output.lower()

    def test_init_creates_dotman_dir_parents(self, runner, tmp_path, monkeypatch):
        """Test init creates .dotman directory with parents if needed."""
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        sub_dir = tmp_path / "nested" / "path"
        sub_dir.mkdir(parents=True)
        monkeypatch.chdir(sub_dir)

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (sub_dir / ".dotman").exists()
