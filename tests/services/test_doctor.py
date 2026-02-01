"""Unit tests for the doctor service module."""

import shutil
from unittest.mock import patch

from dotman.services.doctor import (
    DoctorCheckResult,
    DoctorCommandResult,
    ExecutableChecker,
)


class TestExecutableChecker:
    """Test ExecutableChecker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = ExecutableChecker()

    def test_checker_initializes_with_empty_cache(self):
        """Test that checker initializes with empty cache."""
        assert self.checker.get_cache_size() == 0

    def test_find_executable_for_nonexistent(self):
        """Test finding a non-existent executable."""
        result = self.checker.find_executable("nonexistent_command_xyz_123")
        assert result == (False, None)

    def test_find_executable_for_python(self):
        """Test finding Python executable which should exist."""
        result = self.checker.find_executable("python3")
        assert result[0] is True
        assert result[1] is not None
        assert "python" in result[1].lower()

    def test_find_executable_for_sh(self):
        """Test finding sh executable which should exist on Unix-like systems."""
        result = self.checker.find_executable("sh")
        if shutil.which("sh") is not None:
            assert result[0] is True
            assert result[1] is not None
        else:
            assert result == (False, None)

    def test_find_executable_caches_result(self):
        """Test that find_executable caches results."""
        self.checker.find_executable("python3")
        assert self.checker.get_cache_size() == 1

        self.checker.find_executable("python3")
        assert self.checker.get_cache_size() == 1

    def test_find_executable_returns_same_result_from_cache(self):
        """Test that cached results are returned consistently."""
        result1 = self.checker.find_executable("python3")
        result2 = self.checker.find_executable("python3")
        assert result1 == result2

    def test_find_executable_with_empty_string(self):
        """Test that empty string returns not found."""
        result = self.checker.find_executable("")
        assert result == (False, None)

    def test_find_executable_with_whitespace_only(self):
        """Test that whitespace-only string returns not found."""
        result = self.checker.find_executable("   ")
        assert result == (False, None)

    def test_find_executable_with_special_characters(self):
        """Test handling of special characters in executable name."""
        result = self.checker.find_executable("test;echo")
        assert result == (False, None)

    def test_find_executable_with_leading_whitespace(self):
        """Test handling of leading whitespace."""
        result = self.checker.find_executable("  python3")
        assert result[0] is True

    def test_find_executable_with_trailing_whitespace(self):
        """Test handling of trailing whitespace."""
        result = self.checker.find_executable("python3  ")
        assert result[0] is True

    def test_find_executables_multiple(self):
        """Test finding multiple executables at once."""
        names = ["python3", "nonexistent_xyz", "sh"]
        results = self.checker.find_executables(names)

        assert len(results) == 3
        assert results["python3"][0] is True
        assert results["nonexistent_xyz"] == (False, None)
        if shutil.which("sh") is not None:
            assert results["sh"][0] is True

    def test_clear_cache(self):
        """Test clearing the cache."""
        self.checker.find_executable("python3")
        assert self.checker.get_cache_size() == 1

        self.checker.clear_cache()
        assert self.checker.get_cache_size() == 0

    def test_clear_cache_allows_new_lookups(self):
        """Test that clearing cache allows fresh lookups."""
        result1 = self.checker.find_executable("python3")
        self.checker.clear_cache()
        result2 = self.checker.find_executable("python3")

        assert result1 == result2
        assert self.checker.get_cache_size() == 1

    def test_find_executable_path_is_valid(self):
        """Test that returned path is a valid executable path."""
        result = self.checker.find_executable("python3")
        if result[0] is True:
            assert result[1] is not None
            assert "/" in result[1] or "\\" in result[1]

    def test_find_executable_with_mock_which(self):
        """Test find_executable with mocked shutil.which."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/custom_exec"

            result = self.checker.find_executable("custom_exec")

            assert result == (True, "/usr/bin/custom_exec")
            mock_which.assert_called_once_with("custom_exec")

    def test_find_executable_with_mock_which_not_found(self):
        """Test find_executable with mocked shutil.which returning None."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = self.checker.find_executable("not_found_exec")

            assert result == (False, None)
            mock_which.assert_called_once_with("not_found_exec")

    def test_find_executable_raises_oserror(self):
        """Test handling when shutil.which raises OSError."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = OSError("PATH environment variable not set")

            result = self.checker.find_executable("test_exec")

            assert result == (False, None)

    def test_find_executable_raises_type_error(self):
        """Test handling when shutil.which raises TypeError."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = TypeError("Invalid argument type")

            result = self.checker.find_executable("test_exec")

            assert result == (False, None)

    def test_find_executable_raises_value_error(self):
        """Test handling when shutil.which raises ValueError."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = ValueError("Empty executable name")

            result = self.checker.find_executable("test_exec")

            assert result == (False, None)

    def test_cache_persists_across_calls(self):
        """Test that cache persists across multiple different lookups."""
        self.checker.find_executable("python3")
        self.checker.find_executable("ls")
        self.checker.find_executable("cat")

        assert self.checker.get_cache_size() == 3

    def test_case_sensitive_lookup(self):
        """Test that executable lookup is case sensitive on Unix."""
        shutil.which("Python3")
        result = self.checker.find_executable("Python3")

        if shutil.which("Python3") is not None:
            assert result[0] is True
        else:
            assert result == (False, None)


class TestDoctorCheckResult:
    """Test DoctorCheckResult model."""

    def test_create_result_found_error(self):
        """Test creating a result for a found executable with error severity."""
        result = DoctorCheckResult(
            package_name="nvim-base",
            executable_name="nvim",
            found=True,
            path="/usr/bin/nvim",
            severity="error",
        )
        assert result.package_name == "nvim-base"
        assert result.executable_name == "nvim"
        assert result.found is True
        assert result.path == "/usr/bin/nvim"
        assert result.severity == "error"

    def test_create_result_missing_warning(self):
        """Test creating a result for a missing executable with warning severity."""
        result = DoctorCheckResult(
            package_name="opencode",
            executable_name="bun",
            found=False,
            path=None,
            severity="warning",
        )
        assert result.package_name == "opencode"
        assert result.executable_name == "bun"
        assert result.found is False
        assert result.path is None
        assert result.severity == "warning"

    def test_create_result_missing_error(self):
        """Test creating a result for a missing executable with error severity."""
        result = DoctorCheckResult(
            package_name="zsh",
            executable_name="zsh",
            found=False,
            path=None,
            severity="error",
        )
        assert result.found is False
        assert result.severity == "error"

    def test_result_with_path(self):
        """Test result with actual path."""
        result = DoctorCheckResult(
            package_name="test-pkg",
            executable_name="python3",
            found=True,
            path="/usr/bin/python3",
            severity="warning",
        )
        assert result.path == "/usr/bin/python3"
        assert "/" in result.path

    def test_severity_must_be_error_or_warning(self):
        """Test that severity must be either 'error' or 'warning'."""
        result = DoctorCheckResult(
            package_name="test",
            executable_name="test",
            found=True,
            path="/usr/bin/test",
            severity="error",
        )
        assert result.severity in ("error", "warning")

        result2 = DoctorCheckResult(
            package_name="test",
            executable_name="test",
            found=True,
            path="/usr/bin/test",
            severity="warning",
        )
        assert result2.severity in ("error", "warning")


class TestDoctorCommandResult:
    """Test DoctorCommandResult model."""

    def test_create_empty_result(self):
        """Test creating a result with no checks."""
        result = DoctorCommandResult(package_name="test-pkg")
        assert result.package_name == "test-pkg"
        assert result.checks == []
        assert result.summary == {}

    def test_create_result_with_checks(self):
        """Test creating a result with checks."""
        check1 = DoctorCheckResult(
            package_name="test-pkg",
            executable_name="cmd1",
            found=True,
            path="/usr/bin/cmd1",
            severity="error",
        )
        check2 = DoctorCheckResult(
            package_name="test-pkg",
            executable_name="cmd2",
            found=False,
            path=None,
            severity="warning",
        )
        result = DoctorCommandResult(package_name="test-pkg", checks=[check1, check2])
        assert len(result.checks) == 2
        assert result.checks[0].executable_name == "cmd1"
        assert result.checks[1].executable_name == "cmd2"

    def test_compute_summary_all_passed(self):
        """Test computing summary when all checks passed."""
        check1 = DoctorCheckResult(
            package_name="test-pkg",
            executable_name="cmd1",
            found=True,
            path="/usr/bin/cmd1",
            severity="error",
        )
        check2 = DoctorCheckResult(
            package_name="test-pkg",
            executable_name="cmd2",
            found=True,
            path="/usr/bin/cmd2",
            severity="warning",
        )
        result = DoctorCommandResult(package_name="test-pkg", checks=[check1, check2])
        summary = result.compute_summary()

        assert summary["errors"] == 0
        assert summary["warnings"] == 0
        assert summary["passed"] == 2

    def test_compute_summary_with_errors_and_warnings(self):
        """Test computing summary with errors, warnings, and passed."""
        checks = [
            DoctorCheckResult(
                package_name="test-pkg",
                executable_name="cmd1",
                found=True,
                path="/usr/bin/cmd1",
                severity="error",
            ),
            DoctorCheckResult(
                package_name="test-pkg",
                executable_name="cmd2",
                found=False,
                path=None,
                severity="error",
            ),
            DoctorCheckResult(
                package_name="test-pkg",
                executable_name="cmd3",
                found=False,
                path=None,
                severity="warning",
            ),
            DoctorCheckResult(
                package_name="test-pkg",
                executable_name="cmd4",
                found=True,
                path="/usr/bin/cmd4",
                severity="warning",
            ),
        ]
        result = DoctorCommandResult(package_name="test-pkg", checks=checks)
        summary = result.compute_summary()

        assert summary["errors"] == 1
        assert summary["warnings"] == 1
        assert summary["passed"] == 2

    def test_compute_summary_all_missing(self):
        """Test computing summary when all executables are missing."""
        checks = [
            DoctorCheckResult(
                package_name="test-pkg",
                executable_name="cmd1",
                found=False,
                path=None,
                severity="error",
            ),
            DoctorCheckResult(
                package_name="test-pkg",
                executable_name="cmd2",
                found=False,
                path=None,
                severity="warning",
            ),
        ]
        result = DoctorCommandResult(package_name="test-pkg", checks=checks)
        summary = result.compute_summary()

        assert summary["errors"] == 1
        assert summary["warnings"] == 1
        assert summary["passed"] == 0

    def test_compute_summary_empty(self):
        """Test computing summary for empty checks."""
        result = DoctorCommandResult(package_name="test-pkg")
        summary = result.compute_summary()

        assert summary["errors"] == 0
        assert summary["warnings"] == 0
        assert summary["passed"] == 0

    def test_update_summary(self):
        """Test that summary is updated correctly."""
        result = DoctorCommandResult(package_name="test-pkg")

        check = DoctorCheckResult(
            package_name="test-pkg",
            executable_name="cmd1",
            found=False,
            path=None,
            severity="error",
        )
        result.checks.append(check)
        result.summary = result.compute_summary()

        assert result.summary["errors"] == 1
        assert result.summary["warnings"] == 0
        assert result.summary["passed"] == 0

    def test_multiple_packages_results(self):
        """Test storing results for multiple packages."""
        result1 = DoctorCommandResult(
            package_name="pkg1",
            checks=[
                DoctorCheckResult(
                    package_name="pkg1",
                    executable_name="cmd1",
                    found=True,
                    path="/usr/bin/cmd1",
                    severity="error",
                )
            ],
        )
        result2 = DoctorCommandResult(
            package_name="pkg2",
            checks=[
                DoctorCheckResult(
                    package_name="pkg2",
                    executable_name="cmd2",
                    found=False,
                    path=None,
                    severity="error",
                )
            ],
        )

        assert result1.package_name == "pkg1"
        assert result1.checks[0].found is True
        assert result2.package_name == "pkg2"
        assert result2.checks[0].found is False
