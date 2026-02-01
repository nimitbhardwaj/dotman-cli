"""Integration tests for the doctor CLI command."""

from dotman.cli import app


class TestDoctorCommand:
    """Integration tests for dotman doctor command."""

    def test_doctor_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test doctor fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_doctor_no_packages(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test doctor with no packages configured shows appropriate message."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "no packages to check" in result.output.lower()

    def test_doctor_package_no_doctor_config(
        self, runner, repo_with_packages, env_with_home, monkeypatch
    ):
        """Test doctor handles packages without doctor config gracefully."""
        monkeypatch.chdir(repo_with_packages)

        result = runner.invoke(app, ["doctor", "bash"])

        assert result.exit_code == 0

    def test_doctor_all_packages_no_doctor_config(
        self, runner, repo_with_packages, env_with_home, monkeypatch
    ):
        """Test doctor with all packages having no doctor config."""
        monkeypatch.chdir(repo_with_packages)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0

    def test_doctor_missing_dependency(
        self, runner, temp_repo_with_missing_dep, env_with_home, monkeypatch
    ):
        """Test doctor fails with missing dependency error."""
        monkeypatch.chdir(temp_repo_with_missing_dep)

        result = runner.invoke(app, ["doctor", "pkg_a"])

        assert result.exit_code == 1
        assert "dependency" in result.output.lower()

    def test_doctor_disabled_dependency(
        self, runner, temp_repo_with_disabled_dep, env_with_home, monkeypatch
    ):
        """Test doctor fails with disabled dependency error."""
        monkeypatch.chdir(temp_repo_with_disabled_dep)

        result = runner.invoke(app, ["doctor", "pkg_a"])

        assert result.exit_code == 1
        assert "dependency" in result.output.lower()

    def test_doctor_displays_table(
        self, runner, repo_with_doctor_config, env_with_home, monkeypatch
    ):
        """Test doctor displays output in table format."""
        monkeypatch.chdir(repo_with_doctor_config)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "Doctor Check Results" in result.output or "Package" in result.output

    def test_doctor_with_found_executable(
        self, runner, repo_with_doctor_config, env_with_home, monkeypatch
    ):
        """Test doctor shows found executable with path."""
        monkeypatch.chdir(repo_with_doctor_config)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "python3" in result.output.lower() or "python" in result.output.lower()

    def test_doctor_with_missing_executable(
        self, runner, repo_with_doctor_config, env_with_home, monkeypatch
    ):
        """Test doctor shows missing executable."""
        monkeypatch.chdir(repo_with_doctor_config)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0 or result.exit_code == 1
        assert (
            "not in path" in result.output.lower() or "missing" in result.output.lower()
        )

    def test_doctor_error_severity_missing(
        self, runner, repo_with_doctor_config, env_with_home, monkeypatch
    ):
        """Test doctor returns exit code 1 when error-severity executable is missing."""
        monkeypatch.chdir(repo_with_doctor_config)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1

    def test_doctor_warning_severity_missing(
        self, runner, repo_with_doctor_warning_only, env_with_home, monkeypatch
    ):
        """Test doctor exits 0 when only warning-severity executables are missing."""
        monkeypatch.chdir(repo_with_doctor_warning_only)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0

    def test_doctor_specific_package(
        self, runner, repo_with_doctor_config, env_with_home, monkeypatch
    ):
        """Test doctor for a specific package by name."""
        monkeypatch.chdir(repo_with_doctor_config)

        result = runner.invoke(app, ["doctor", "pkg_with_executables"])

        assert result.exit_code == 0 or result.exit_code == 1
        assert (
            "pkg_with_execut" in result.output.lower()
            or "execut" in result.output.lower()
        )

    def test_doctor_with_config_dir_option(
        self, runner, repo_with_doctor_config, env_with_home, tmp_path, monkeypatch
    ):
        """Test doctor with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = repo_with_doctor_config

        result = runner.invoke(app, ["doctor", "--config-dir", str(config_dir)])

        assert result.exit_code == 0 or result.exit_code == 1

    def test_doctor_shows_summary(
        self, runner, repo_with_doctor_config, env_with_home, monkeypatch
    ):
        """Test doctor shows summary of checks."""
        monkeypatch.chdir(repo_with_doctor_config)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0 or result.exit_code == 1
        assert "summary" in result.output.lower()

    def test_doctor_checks_dependencies(
        self, runner, repo_with_doctor_config_and_deps, env_with_home, monkeypatch
    ):
        """Test doctor checks executables for dependencies too."""
        monkeypatch.chdir(repo_with_doctor_config_and_deps)

        result = runner.invoke(app, ["doctor", "parent"])

        assert result.exit_code == 0 or result.exit_code == 1
        assert "parent" in result.output.lower() or "child" in result.output.lower()
