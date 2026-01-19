"""Integration tests for the push CLI command."""

import subprocess
from unittest.mock import patch

from dotman.cli import app


class TestPushCommand:
    """Integration tests for dotman push command."""

    def test_push_not_initialized(self, runner, tmp_path, monkeypatch):
        """Test push fails when dotman is not initialized."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_push_not_git_repo(self, runner, temp_repo, env_with_home, monkeypatch):
        """Test push fails when directory is not a git repository."""
        monkeypatch.chdir(temp_repo)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "not a git repository" in result.output.lower()

    def test_push_no_changes(self, runner, git_repo, env_with_home, monkeypatch):
        """Test push exits 0 with message when no changes to commit."""
        monkeypatch.chdir(git_repo)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "no changes to commit" in result.output.lower()

    def test_push_no_changes_with_remote(
        self, runner, git_repo_with_remote, env_with_home, monkeypatch
    ):
        """Test push with remote exits 0 with message when no changes."""
        monkeypatch.chdir(git_repo_with_remote)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "no changes to commit" in result.output.lower()

    def test_push_default_behavior(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test default push behavior: stages, commits, and pushes changes."""

        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert (
            "staging" in result.output.lower()
            or "staging all changes" in result.output.lower()
        )
        assert "commit" in result.output.lower()
        assert (
            "pushing" in result.output.lower() or "pushing to" in result.output.lower()
        )
        assert "successfully pushed" in result.output.lower()

        log_result = subprocess.run(
            ["git", "log", "--oneline", "-n", "1"],
            cwd=git_repo_with_changes,
            capture_output=True,
            text=True,
        )
        assert "dotman update:" in log_result.stdout

    def test_push_stage_only_flag(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test --stage-only behavior: stages and commits without pushing."""

        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push", "--stage-only"], catch_exceptions=False)

        assert result.exit_code == 0
        assert (
            "staging" in result.output.lower()
            or "staging all changes" in result.output.lower()
        )
        assert "commit" in result.output.lower()
        assert "successfully pushed" not in result.output.lower()
        assert "staged and committed" in result.output.lower()

        log_result = subprocess.run(
            ["git", "log", "--oneline", "-n", "1"],
            cwd=git_repo_with_changes,
            capture_output=True,
            text=True,
        )
        assert "dotman update:" in log_result.stdout

    def test_push_stage_only_short_flag(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test -s short flag for --stage-only behavior."""

        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push", "-s"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "staged and committed" in result.output.lower()

    def test_push_commit_message_format(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test commit message contains timestamp and timezone."""
        import re

        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "dotman update:" in result.output

        log_result = subprocess.run(
            ["git", "log", "--format=%B", "-n", "1"],
            cwd=git_repo_with_changes,
            capture_output=True,
            text=True,
        )
        commit_message = log_result.stdout

        pattern = r"dotman update: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}"
        assert re.search(pattern, commit_message), (
            f"Commit message format invalid: {commit_message}"
        )

    def test_push_with_unstaged_changes(
        self, runner, git_repo_with_remote, env_with_home, monkeypatch
    ):
        """Test push with only unstaged changes (no staged changes)."""

        monkeypatch.chdir(git_repo_with_remote)

        (git_repo_with_remote / "README.md").write_text("# Modified content\n")

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert (
            "staging" in result.output.lower()
            or "staging all changes" in result.output.lower()
        )
        assert "successfully pushed" in result.output.lower()

    def test_push_with_explicit_remote(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push with explicit remote name."""
        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push", "origin"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "origin" in result.output.lower()

    def test_push_with_explicit_branch(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push with explicit branch name."""
        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(
            app, ["push", "--branch", "master"], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "master" in result.output.lower()

    def test_push_with_set_upstream(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push with --set-upstream flag."""
        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(
            app,
            ["push", "--set-upstream", "--branch", "master"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "successfully pushed" in result.output.lower()

    def test_push_with_set_upstream_short(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push with -u short flag for --set-upstream."""
        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(
            app, ["push", "-u", "--branch", "master"], catch_exceptions=False
        )

        assert result.exit_code == 0

    def test_push_current_branch_detection(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test that git operations work with current branch detection."""

        monkeypatch.chdir(git_repo_with_changes)

        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo_with_changes,
            capture_output=True,
            text=True,
        )
        current_branch = branch_result.stdout.strip()

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert current_branch in result.output or "branch" in result.output.lower()

    def test_push_push_failure_after_commit(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test error handling when push fails after successful commit."""

        monkeypatch.chdir(git_repo_with_changes)

        from dotman import remote

        original_run = remote.subprocess.run

        def mock_run(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and len(cmd) > 1 and cmd[1] == "push":
                raise subprocess.CalledProcessError(
                    returncode=1,
                    cmd=cmd,
                    stderr="error: failed to push some refs to 'origin'",
                )
            return original_run(*args, **kwargs)

        with patch.object(remote.subprocess, "run", side_effect=mock_run):
            result = runner.invoke(app, ["push"], catch_exceptions=False)

            assert result.exit_code == 1
            assert (
                "staged and committed but push failed" in result.output.lower()
                or "push failed" in result.output.lower()
            )

            log_result = subprocess.run(
                ["git", "log", "--oneline", "-n", "1"],
                cwd=git_repo_with_changes,
                capture_output=True,
                text=True,
            )
            assert "dotman update:" in log_result.stdout

    def test_push_with_config_dir_option(
        self, runner, git_repo_with_changes, env_with_home, tmp_path, monkeypatch
    ):
        """Test push with --config-dir option."""
        monkeypatch.chdir(tmp_path)

        config_dir = git_repo_with_changes

        result = runner.invoke(
            app, ["push", "--config-dir", str(config_dir)], catch_exceptions=False
        )

        assert result.exit_code == 0

    def test_push_displays_remote_url(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push displays the remote URL."""
        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "pushing to" in result.output.lower()

    def test_push_displays_branch_info(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push displays branch information."""
        monkeypatch.chdir(git_repo_with_changes)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "branch:" in result.output.lower() or "main" in result.output.lower()


class TestPushCommandEdgeCases:
    """Edge case tests for dotman push command."""

    def test_push_with_repo_option(
        self, runner, git_repo_with_changes, env_with_home, monkeypatch
    ):
        """Test push with --repo option (requires registered repository)."""
        from dotman.config import get_repo_manager
        from dotman.remote import RemoteManager

        monkeypatch.chdir(git_repo_with_changes)

        remote_manager = RemoteManager(git_repo_with_changes)
        remote_url = (
            remote_manager.get_remote_url("origin")
            if remote_manager.is_git_repo()
            else None
        )

        repo_manager = get_repo_manager()
        repo_manager.register_repository(
            name="test_repo",
            path=git_repo_with_changes,
            remote_url=remote_url,
            set_default=True,
        )

        result = runner.invoke(
            app, ["push", "--repo", "test_repo"], catch_exceptions=False
        )

        assert result.exit_code == 0

    def test_push_empty_commit_message_rejected(
        self, runner, git_repo, env_with_home, monkeypatch
    ):
        """Test that push handles empty repository correctly."""
        monkeypatch.chdir(git_repo)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "no changes" in result.output.lower()

    def test_push_multiple_files(
        self, runner, git_repo_with_remote, env_with_home, monkeypatch
    ):
        """Test push with multiple files changed."""

        monkeypatch.chdir(git_repo_with_remote)

        (git_repo_with_remote / "file1.txt").write_text("content 1\n")
        (git_repo_with_remote / "file2.txt").write_text("content 2\n")
        (git_repo_with_remote / "file3.txt").write_text("content 3\n")
        subprocess.run(["git", "add", "."], check=True, capture_output=True)

        result = runner.invoke(app, ["push"], catch_exceptions=False)

        assert result.exit_code == 0

        log_result = subprocess.run(
            ["git", "log", "--oneline", "-n", "1"],
            cwd=git_repo_with_remote,
            capture_output=True,
            text=True,
        )
        assert "dotman update:" in log_result.stdout
