"""Integration tests for the undeploy CLI command."""

from dotman.cli import app


class TestUndeployCommand:
    """Integration tests for dotman undeploy command."""

    def test_undeploy_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test undeploy fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["undeploy"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_undeploy_no_packages(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test undeploy with no packages enabled shows appropriate message."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 0
        assert "no packages to undeploy" in result.output.lower()

    def test_undeploy_specific_package(
        self, runner, deployed_repo_with_symlinks, env_with_home, monkeypatch
    ):
        """Test undeploying a specific package by name."""
        monkeypatch.chdir(deployed_repo_with_symlinks)

        result = runner.invoke(app, ["undeploy", "bash"])

        assert result.exit_code == 0
        assert (
            "bash" in result.output.lower()
            or "undeploying package" in result.output.lower()
        )

    def test_undeploy_all_enabled_packages(
        self, runner, deployed_repo_with_symlinks, env_with_home, monkeypatch
    ):
        """Test undeploying all enabled packages."""
        monkeypatch.chdir(deployed_repo_with_symlinks)

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 0
        assert (
            "bash" in result.output.lower()
            or "undeploying package" in result.output.lower()
        )

    def test_undeploy_nonexistent_package(
        self, runner, temp_repo_with_simple_package, env_with_home, monkeypatch
    ):
        """Test undeploying a package that doesn't exist in config."""
        monkeypatch.chdir(temp_repo_with_simple_package)

        result = runner.invoke(app, ["undeploy", "nonexistent"])

        assert result.exit_code == 1
        assert (
            "not found" in result.output.lower()
            or "dependency" in result.output.lower()
        )

    def test_undeploy_circular_dependency(
        self, runner, repo_with_circular_dependency, env_with_home, monkeypatch
    ):
        """Test undeploy fails with circular dependency error."""
        monkeypatch.chdir(repo_with_circular_dependency)

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 1
        assert result.exception is not None
        exc_str = str(result.exception).lower()
        assert (
            "circular" in exc_str or "dependency" in exc_str or "recursion" in exc_str
        )

    def test_undeploy_removes_symlinks(
        self,
        runner,
        deployed_repo_with_symlinks,
        env_with_home,
        monkeypatch,
        home_dir,
    ):
        """Test undeploy removes symlinks correctly."""
        monkeypatch.chdir(deployed_repo_with_symlinks)

        bashrc_link = home_dir / ".bashrc"
        assert bashrc_link.is_symlink(), "Symlink should exist before undeploy"

        result = runner.invoke(app, ["undeploy", "bash"])

        assert result.exit_code == 0
        assert (
            "removed" in result.output.lower()
            or "undeploy complete" in result.output.lower()
        )
        assert not bashrc_link.exists(), "Symlink should be removed after undeploy"

    def test_undeploy_skips_non_symlinks(
        self,
        runner,
        deployed_repo_with_regular_files,
        env_with_home,
        monkeypatch,
        home_dir,
    ):
        """Test undeploy skips regular files (not symlinks)."""
        monkeypatch.chdir(deployed_repo_with_regular_files)

        bashrc_file = home_dir / ".bashrc"
        assert bashrc_file.exists(), "Regular file should exist before undeploy"
        assert not bashrc_file.is_symlink(), (
            "Target should be a regular file, not symlink"
        )

        result = runner.invoke(app, ["undeploy", "bash"])

        assert result.exit_code == 0
        assert (
            "not a symlink" in result.output.lower()
            or "skipping" in result.output.lower()
            or "conflict" in result.output.lower()
        )
        assert bashrc_file.exists(), "Regular file should still exist after undeploy"

    def test_undeploy_missing_dependency(
        self, runner, temp_repo_with_missing_dep, env_with_home, monkeypatch
    ):
        """Test undeploy fails when a dependency is not defined."""
        monkeypatch.chdir(temp_repo_with_missing_dep)

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 1
        assert "dependency" in result.output.lower()

    def test_undeploy_disabled_dependency(
        self, runner, temp_repo_with_disabled_dep, env_with_home, monkeypatch
    ):
        """Test undeploy fails when a dependency is not enabled."""
        monkeypatch.chdir(temp_repo_with_disabled_dep)

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 1
        assert "dependency" in result.output.lower()

    def test_undeploy_complete_message(
        self, runner, deployed_repo_with_symlinks, env_with_home, monkeypatch
    ):
        """Test undeploy shows complete message at the end."""
        monkeypatch.chdir(deployed_repo_with_symlinks)

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 0
        assert "complete" in result.output.lower()

    def test_undeploy_with_config_dir_option(
        self,
        runner,
        deployed_repo_with_symlinks,
        env_with_home,
        tmp_path,
        monkeypatch,
    ):
        """Test undeploy with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = deployed_repo_with_symlinks

        result = runner.invoke(
            app, ["undeploy", "--config-dir", str(config_dir), "bash"]
        )

        assert result.exit_code == 0

    def test_undeploy_multiple_packages(
        self,
        runner,
        deployed_repo_with_multiple_symlinks,
        env_with_home,
        monkeypatch,
        home_dir,
    ):
        """Test undeploying multiple packages removes all symlinks."""
        monkeypatch.chdir(deployed_repo_with_multiple_symlinks)

        bashrc_link = home_dir / ".bashrc"
        vimrc_link = home_dir / ".vimrc"

        assert bashrc_link.is_symlink(), "bashrc symlink should exist"
        assert vimrc_link.is_symlink(), "vimrc symlink should exist"

        result = runner.invoke(app, ["undeploy"])

        assert result.exit_code == 0
        assert not bashrc_link.exists(), "bashrc symlink should be removed"
        assert not vimrc_link.exists(), "vimrc symlink should be removed"

    def test_undeploy_not_deployed_package(
        self, runner, repo_with_source_files, env_with_home, monkeypatch
    ):
        """Test undeploying a package that was never deployed."""
        monkeypatch.chdir(repo_with_source_files)

        result = runner.invoke(app, ["undeploy", "bash"])

        assert result.exit_code == 0
        assert (
            "not deployed" in result.output.lower()
            or "does not exist" in result.output.lower()
        )
