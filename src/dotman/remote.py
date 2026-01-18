"""Remote repository management for Dotman."""

import subprocess
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from dotman.exceptions import (
    NothingToCommitError,
    RemoteAuthenticationError,
    RemoteCloneError,
    RemoteFetchError,
    RemoteNotFoundError,
    RemotePushError,
)


class RemoteRepoConfig(BaseModel):
    """Configuration for a remote repository."""

    name: str
    url: str
    branch: str = "main"
    auth_type: str | None = None
    auth_token: str | None = None


class RemoteManager:
    """Manages remote repository operations."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir

    def _run_git_command(
        self,
        args: list[str],
        cwd: Path | None = None,
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess | subprocess.CalledProcessError:
        """Run a git command.

        Args:
            args: Git command arguments
            cwd: Working directory (defaults to repo_dir)
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise on non-zero exit code

        Returns:
            CompletedProcess result

        Raises:
            RemoteCloneError: If the git command fails and check is True
        """
        cwd = cwd or self.repo_dir
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                check=check,
            )
            return result
        except subprocess.CalledProcessError as e:
            if check:
                raise RemoteCloneError(f"Git command failed: {e.stderr}") from e
            return e

    def _format_repo_url(self, url: str, auth_token: str | None = None) -> str:
        """Format repository URL for cloning.

        Args:
            url: The repository URL
            auth_token: Optional authentication token

        Returns:
            Formatted URL with authentication if provided
        """
        if auth_token:
            if "github.com" in url:
                if url.endswith(".git"):
                    url = url[:-4]
                return (
                    f"https://{auth_token}@github.com{url[url.index('github.com') :]}"
                )
            elif "gitlab.com" in url:
                if url.endswith(".git"):
                    url = url[:-4]
                return (
                    f"https://oauth2:{auth_token}@gitlab.com"
                    f"{url[url.index('gitlab.com') :]}"
                )
        return url

    def clone(
        self,
        url: str,
        target_dir: Path | None = None,
        branch: str = "main",
        auth_token: str | None = None,
        depth: int | None = None,
    ) -> Path:
        """Clone a remote repository.

        Args:
            url: The repository URL (supports GitHub/GitLab shorthand like user/repo)
            target_dir: Target directory for the clone (defaults to repo_dir)
            branch: Branch to clone
            auth_token: Optional authentication token
            depth: Optional shallow clone depth

        Returns:
            Path to the cloned repository

        Raises:
            RemoteNotFoundError: If the repository is not found
            RemoteAuthenticationError: If authentication fails
            RemoteCloneError: If cloning fails for other reasons
        """
        target_dir = target_dir or self.repo_dir

        formatted_url = self._format_repo_url(url, auth_token)

        cmd = ["clone"]
        if depth:
            cmd.extend(["--depth", str(depth)])
        if branch and branch != "main":
            cmd.extend(["--branch", branch])

        cmd.extend([formatted_url, str(target_dir)])

        try:
            self._run_git_command(cmd)
        except RemoteCloneError as e:
            error_msg = str(e)
            if (
                "Could not resolve host" in error_msg
                or "not found" in error_msg.lower()
            ):
                raise RemoteNotFoundError(f"Repository not found: {url}") from e
            elif "Authentication failed" in error_msg:
                raise RemoteAuthenticationError(
                    f"Authentication failed for: {url}"
                ) from e
            raise

        if not target_dir.exists():
            raise RemoteCloneError(f"Clone failed: {target_dir} was not created")

        self._run_git_command(["lfs", "install"], cwd=target_dir)

        return target_dir

    def fetch(
        self,
        remote: str = "origin",
        branch: str | None = None,
    ) -> None:
        """Fetch updates from remote repository.

        Args:
            remote: Remote name
            branch: Specific branch to fetch (fetches all if None)

        Raises:
            RemoteFetchError: If fetch fails
        """
        cmd = ["fetch", remote]
        if branch:
            cmd.append(branch)

        try:
            self._run_git_command(cmd)
        except RemoteCloneError as e:
            raise RemoteFetchError(f"Failed to fetch from {remote}: {e}") from e

    def pull(self, remote: str = "origin", branch: str = "main") -> None:
        """Pull updates from remote repository.

        Args:
            remote: Remote name
            branch: Branch to pull

        Raises:
            RemoteFetchError: If pull fails
        """
        try:
            self._run_git_command(["pull", remote, branch])
        except RemoteCloneError as e:
            raise RemoteFetchError(f"Failed to pull from {remote}: {e}") from e

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = False,
    ) -> None:
        """Push changes to remote repository.

        Args:
            remote: Remote name
            branch: Branch to push (defaults to current branch)
            set_upstream: Whether to set upstream tracking

        Raises:
            RemotePushError: If push fails
        """
        cmd = ["push"]
        if set_upstream:
            cmd.append("--set-upstream")
        cmd.append(remote)
        if branch:
            cmd.append(branch)

        try:
            self._run_git_command(cmd)
        except RemoteCloneError as e:
            raise RemotePushError(f"Failed to push to {remote}: {e}") from e

    def checkout(self, branch: str, create: bool = False) -> None:
        """Checkout a branch.

        Args:
            branch: Branch name
            create: Whether to create the branch if it doesn't exist

        Raises:
            RemoteCloneError: If checkout fails
        """
        cmd = ["checkout"]
        if create:
            cmd.append("-b")
        cmd.append(branch)

        try:
            self._run_git_command(cmd)
        except RemoteCloneError as e:
            raise RemoteCloneError(f"Failed to checkout {branch}: {e}") from e

    def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Current branch name
        """
        result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return cast(str, result.stdout).strip()

    def get_remote_url(self, remote: str = "origin") -> str:
        """Get the URL of a remote.

        Args:
            remote: Remote name

        Returns:
            Remote URL
        """
        result = self._run_git_command(["remote", "get-url", remote])
        return cast(str, result.stdout).strip()

    def is_git_repo(self, path: Path | None = None) -> bool:
        """Check if a path is a git repository.

        Args:
            path: Path to check (defaults to repo_dir)

        Returns:
            True if it's a git repository
        """
        check_path = path or self.repo_dir
        git_dir = check_path / ".git"
        return git_dir.exists()

    def init_repo(self) -> None:
        """Initialize a new git repository.

        Args:
            path: Path to initialize
        """
        self._run_git_command(["init"])

    def stage_all(self) -> None:
        """Stage all changes in the repository.

        Raises:
            RemoteCloneError: If staging fails
        """
        self._run_git_command(["add", "-A"])

    def commit(self, message: str) -> None:
        """Commit staged changes.

        Args:
            message: Commit message

        Raises:
            NothingToCommitError: If there are no staged changes to commit
            RemoteCloneError: If commit fails for other reasons
        """
        try:
            self._run_git_command(["commit", "-m", message])
        except RemoteCloneError as e:
            if "nothing to commit" in str(e).lower():
                raise NothingToCommitError("No changes to commit") from e
            raise

    def has_staged_changes(self) -> bool:
        """Check if there are staged changes.

        Returns:
            True if there are staged changes, False otherwise
        """
        try:
            self._run_git_command(["diff", "--cached", "--quiet"], check=False)
            return False
        except RemoteCloneError:
            return True

    def has_unstaged_changes(self) -> bool:
        """Check if there are unstaged changes.

        Returns:
            True if there are unstaged changes, False otherwise
        """
        try:
            self._run_git_command(["diff", "--quiet"], check=False)
            return False
        except RemoteCloneError:
            return True

    def add_remote(self, name: str, url: str) -> None:
        """Add a remote to the repository.

        Args:
            name: Remote name
            url: Remote URL
        """
        self._run_git_command(["remote", "add", name, url])


def detect_remote_from_string(url: str) -> str:
    """Detect and normalize a remote URL.

    Args:
        url: URL or shorthand (e.g., 'user/repo', 'github:user/repo')

    Returns:
        Normalized full URL
    """
    url = url.strip()

    if url.startswith("github:"):
        url = url.replace("github:", "https://github.com/") + ".git"
    elif url.startswith("gitlab:"):
        url = url.replace("gitlab:", "https://gitlab.com/") + ".git"
    elif "/" in url and not url.startswith("http") and not url.startswith("git@"):
        if url.count("/") == 1:
            url = f"https://github.com/{url}.git"
        elif url.count("/") >= 2:
            parts = url.split("/")
            provider = parts[0]
            repo_path = "/".join(parts[1:])
            if provider in ("github", "gitlab"):
                url = f"https://{provider}.com/{repo_path}.git"

    if not url.endswith(".git") and not url.startswith("git@"):
        url = url + ".git"

    return url
