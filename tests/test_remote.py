"""Tests for remote repository functionality."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from dotman.exceptions import (
    RemoteAuthenticationError,
    RemoteCloneError,
    RemoteFetchError,
    RemoteNotFoundError,
    RemotePushError,
)
from dotman.remote import RemoteManager, detect_remote_from_string


class TestDetectRemoteFromString:
    """Tests for detect_remote_from_string function."""

    def test_github_shorthand(self):
        """Test GitHub shorthand detection."""
        result = detect_remote_from_string("user/repo")
        assert result == "https://github.com/user/repo.git"

    def test_github_full_url(self):
        """Test GitHub full URL."""
        result = detect_remote_from_string("https://github.com/user/repo")
        assert result == "https://github.com/user/repo.git"

    def test_github_full_url_with_git(self):
        """Test GitHub URL with .git extension."""
        result = detect_remote_from_string("https://github.com/user/repo.git")
        assert result == "https://github.com/user/repo.git"

    def test_github_prefix(self):
        """Test GitHub prefix detection."""
        result = detect_remote_from_string("github:user/repo")
        assert result == "https://github.com/user/repo.git"

    def test_gitlab_shorthand(self):
        """Test GitLab shorthand detection."""
        result = detect_remote_from_string("gitlab:user/repo")
        assert result == "https://gitlab.com/user/repo.git"

    def test_gitlab_full_url(self):
        """Test GitLab full URL."""
        result = detect_remote_from_string("https://gitlab.com/user/repo.git")
        assert result == "https://gitlab.com/user/repo.git"

    def test_org_repo_path(self):
        """Test organization repo path."""
        result = detect_remote_from_string("orgname/very-long-repo-name")
        assert result == "https://github.com/orgname/very-long-repo-name.git"

    def test_strips_whitespace(self):
        """Test whitespace stripping."""
        result = detect_remote_from_string("  user/repo  ")
        assert result == "https://github.com/user/repo.git"


class TestRemoteManager:
    """Tests for RemoteManager class."""

    def test_init_with_path(self):
        """Test initialization with a path."""
        manager = RemoteManager(Path("/tmp/test"))
        assert manager.repo_dir == Path("/tmp/test")

    @patch("subprocess.run")
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test"))
        result = manager._run_git_command(["status"])

        assert result.returncode == 0
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_git_command_failure(self, mock_run):
        """Test failed git command execution."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["git", "status"], stderr="error"
        )

        manager = RemoteManager(Path("/tmp/test"))
        with pytest.raises(RemoteCloneError):
            manager._run_git_command(["status"])

    def test_format_repo_url_without_auth(self):
        """Test URL formatting without authentication."""
        manager = RemoteManager(Path("/tmp/test"))
        result = manager._format_repo_url("https://github.com/user/repo.git")
        assert result == "https://github.com/user/repo.git"

    def test_format_repo_url_with_github_auth(self):
        """Test URL formatting with GitHub authentication."""
        manager = RemoteManager(Path("/tmp/test"))
        result = manager._format_repo_url(
            "https://github.com/user/repo.git", auth_token="test_token"
        )
        assert "test_token@github.com" in result

    def test_format_repo_url_with_gitlab_auth(self):
        """Test URL formatting with GitLab authentication."""
        manager = RemoteManager(Path("/tmp/test"))
        result = manager._format_repo_url(
            "https://gitlab.com/user/repo.git", auth_token="test_token"
        )
        assert "oauth2:test_token@gitlab.com" in result

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_clone_command(self, mock_exists, mock_run):
        """Test repository cloning."""
        mock_exists.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "clone"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp"))
        result = manager.clone(
            url="https://github.com/user/repo.git",
            target_dir=Path("/tmp/test_repo"),
        )

        assert result == Path("/tmp/test_repo")
        mock_run.assert_called()

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_clone_creates_lfs_install(self, mock_exists, mock_run):
        """Test that git lfs install is called after clone."""
        mock_exists.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "clone"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp"))
        manager.clone(
            url="https://github.com/user/repo.git",
            target_dir=Path("/tmp/test_repo"),
        )

        calls = mock_run.call_args_list
        lfs_call = [c for c in calls if "lfs" in c[0][0]]
        assert len(lfs_call) > 0

    @patch("subprocess.run")
    def test_clone_not_found_error(self, mock_run):
        """Test error handling when repository not found."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "clone"],
            stderr=(
                "fatal: repository 'https://github.com/nonexistent/repo.git' not found"
            ),
        )

        manager = RemoteManager(Path("/tmp"))
        with pytest.raises(RemoteNotFoundError):
            manager.clone(
                url="https://github.com/nonexistent/repo.git",
                target_dir=Path("/tmp/test_repo"),
            )

    @patch("subprocess.run")
    def test_clone_auth_error(self, mock_run):
        """Test error handling when authentication fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "clone"],
            stderr="Authentication failed",
        )

        manager = RemoteManager(Path("/tmp"))
        with pytest.raises(RemoteAuthenticationError):
            manager.clone(
                url="https://github.com/user/repo.git",
                target_dir=Path("/tmp/test_repo"),
                auth_token="bad_token",
            )

    @patch("subprocess.run")
    def test_fetch(self, mock_run):
        """Test fetching from remote."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "fetch"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.fetch(remote="origin")

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "fetch" in call_args
        assert "origin" in call_args

    @patch("subprocess.run")
    def test_pull(self, mock_run):
        """Test pulling from remote."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "pull"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.pull(remote="origin", branch="main")

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "pull" in call_args

    @patch("subprocess.run")
    def test_push(self, mock_run):
        """Test pushing to remote."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.push(remote="origin", branch="main")

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "push" in call_args
        assert "origin" in call_args
        assert "main" in call_args

    @patch("subprocess.run")
    def test_push_with_upstream(self, mock_run):
        """Test pushing with set-upstream flag."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.push(remote="origin", branch="develop", set_upstream=True)

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "--set-upstream" in call_args
        assert "origin" in call_args
        assert "develop" in call_args

    @patch("subprocess.run")
    def test_push_no_branch_uses_current(self, mock_run):
        """Test push without branch uses current branch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.push(remote="origin", branch=None)

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "push" in call_args

    @patch("subprocess.run")
    def test_push_failure(self, mock_run):
        """Test push failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["git", "push"], stderr="error"
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        with pytest.raises(RemotePushError):
            manager.push(remote="origin", branch="main")

    @patch("subprocess.run")
    def test_checkout(self, mock_run):
        """Test checkout command."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "checkout"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.checkout(branch="develop")

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "checkout" in call_args
        assert "develop" in call_args

    @patch("subprocess.run")
    def test_checkout_create_branch(self, mock_run):
        """Test checkout with branch creation."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "checkout"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.checkout(branch="feature", create=True)

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "-b" in call_args

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run):
        """Test getting current branch name."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse"], returncode=0, stdout="main\n", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        branch = manager.get_current_branch()

        assert branch == "main"

    @patch("subprocess.run")
    def test_get_remote_url(self, mock_run):
        """Test getting remote URL."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "remote"],
            returncode=0,
            stdout="https://github.com/user/repo.git\n",
            stderr="",
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        url = manager.get_remote_url(remote="origin")

        assert url == "https://github.com/user/repo.git"

    def test_is_git_repo_true(self, tmp_path):
        """Test is_git_repo returns True for git repos."""
        (tmp_path / ".git").mkdir()
        manager = RemoteManager(tmp_path)
        assert manager.is_git_repo() is True

    def test_is_git_repo_false(self, tmp_path):
        """Test is_git_repo returns False for non-git paths."""
        manager = RemoteManager(tmp_path)
        assert manager.is_git_repo() is False

    @patch("subprocess.run")
    def test_init_repo(self, mock_run):
        """Test repository initialization."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "init"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/new_repo"))
        manager.init_repo()

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "init" in call_args

    @patch("subprocess.run")
    def test_add_remote(self, mock_run):
        """Test adding remote."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "remote"], returncode=0, stdout="", stderr=""
        )

        manager = RemoteManager(Path("/tmp/test_repo"))
        manager.add_remote(name="origin", url="https://github.com/user/repo.git")

        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "remote" in call_args
        assert "add" in call_args
        assert "origin" in call_args


class TestRemoteExceptions:
    """Tests for remote-related exceptions."""

    def test_remote_error_inheritance(self):
        """Test exception hierarchy."""
        assert issubclass(RemoteCloneError, Exception)
        assert issubclass(RemoteFetchError, Exception)
        assert issubclass(RemoteNotFoundError, Exception)
        assert issubclass(RemoteAuthenticationError, Exception)
        assert issubclass(RemotePushError, Exception)

    def test_remote_clone_error_message(self):
        """Test RemoteCloneError with message."""
        error = RemoteCloneError("Clone failed")
        assert str(error) == "Clone failed"

    def test_remote_fetch_error_message(self):
        """Test RemoteFetchError with message."""
        error = RemoteFetchError("Fetch failed")
        assert str(error) == "Fetch failed"

    def test_remote_push_error_message(self):
        """Test RemotePushError with message."""
        error = RemotePushError("Push failed")
        assert str(error) == "Push failed"
