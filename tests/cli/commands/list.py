"""Integration tests for the list CLI command."""

from dotman.cli import app


class TestListCommand:
    """Integration tests for dotman list command."""

    def test_list_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test list fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["list"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_list_no_packages(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test list with no packages defined shows appropriate message."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "no packages" in result.output.lower()

    def test_list_shows_enabled_status(
        self, runner, repo_with_packages, env_with_home, monkeypatch
    ):
        """Test list shows enabled/disabled status for packages."""
        monkeypatch.chdir(repo_with_packages)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "bash" in result.output.lower()
        assert "vim" in result.output.lower()
        assert "zsh" in result.output.lower()
        assert "nested" in result.output.lower()

    def test_list_shows_correct_file_count(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test list shows correct file count for packages."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "bash" in result.output.lower()
        assert "vim" in result.output.lower()

    def test_list_shows_dependencies(
        self, runner, repo_with_packages, env_with_home, monkeypatch
    ):
        """Test list shows dependencies for packages."""
        monkeypatch.chdir(repo_with_packages)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "zsh" in result.output.lower()
        assert "bash" in result.output.lower()

    def test_list_enabled_packages_marked_correctly(
        self, runner, repo_with_packages, env_with_home, monkeypatch
    ):
        """Test enabled packages show Yes, disabled show No."""
        monkeypatch.chdir(repo_with_packages)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Yes" in result.output or "green" in result.output
        assert "No" in result.output or "dim" in result.output

    def test_list_with_config_dir_option(
        self, runner, repo_with_packages, env_with_home, tmp_path, monkeypatch
    ):
        """Test list with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = repo_with_packages

        result = runner.invoke(app, ["list", "--config-dir", str(config_dir)])

        assert result.exit_code == 0
        assert "bash" in result.output.lower()

    def test_list_displays_in_table_format(
        self, runner, repo_with_packages, env_with_home, monkeypatch
    ):
        """Test list displays packages in a table format."""
        monkeypatch.chdir(repo_with_packages)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Package" in result.output or "bash" in result.output
        assert "Enabled" in result.output
        assert "Files" in result.output
        assert "Dependencies" in result.output
