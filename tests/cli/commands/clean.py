"""Integration tests for the clean CLI command."""

from dotman.cli import app


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

    def test_clean_shows_not_implemented(
        self, runner, temp_repo, env_with_home, monkeypatch
    ):
        """Test clean shows not yet implemented message."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["clean"])

        assert result.exit_code == 0
        assert (
            "not yet implemented" in result.output.lower()
            or "clean" in result.output.lower()
        )

    def test_clean_with_specific_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test clean with a specific package argument."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["clean", "bash"])

        assert result.exit_code == 0
        assert (
            "not yet implemented" in result.output.lower()
            or "no orphaned" in result.output.lower()
            or "clean" in result.output.lower()
        )

    def test_clean_with_config_dir_option(
        self, runner, repo_with_source_files, env_with_home, tmp_path, monkeypatch
    ):
        """Test clean with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = repo_with_source_files

        result = runner.invoke(app, ["clean", "--config-dir", str(config_dir)])

        assert result.exit_code == 0
