"""Pytest fixtures for dotman CLI integration tests."""

import shutil

import pytest
import yaml
from typer.testing import CliRunner


@pytest.fixture
def runner():
    """Provide a Typer CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary dotfiles repository with dotman initialized."""
    repo_dir = tmp_path / "dotfiles"
    repo_dir.mkdir()

    dotman_dir = repo_dir / ".dotman"
    dotman_dir.mkdir()

    config_path = dotman_dir / "config.yaml"
    local_config_path = dotman_dir / "local.yaml"

    default_config = {
        "settings": {
            "backup_dir": ".dotman/backups",
            "template_suffix": ".j2",
        },
        "variables": {},
        "packages": {},
    }

    default_local = {
        "packages": [],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(default_local, f, default_flow_style=False, sort_keys=False)

    yield repo_dir

    if dotman_dir.exists():
        shutil.rmtree(dotman_dir)


@pytest.fixture
def repo_with_packages(temp_repo):
    """Create a temp repo with configured packages."""
    repo_dir = temp_repo
    dotman_dir = repo_dir / ".dotman"
    config_path = dotman_dir / "config.yaml"
    local_config_path = dotman_dir / "local.yaml"

    config = {
        "settings": {
            "backup_dir": ".dotman/backups",
            "template_suffix": ".j2",
        },
        "variables": {"global_var": "global_value"},
        "packages": {
            "bash": {
                "depends": [],
                "files": [{"source": "bash/.bashrc", "target": "~/.bashrc"}],
                "variables": {"shell": "bash"},
            },
            "vim": {
                "depends": [],
                "files": [{"source": "vim/.vimrc", "target": "~/.vimrc"}],
                "variables": {},
            },
            "zsh": {
                "depends": ["bash"],
                "files": [{"source": "zsh/.zshrc", "target": "~/.zshrc"}],
                "variables": {},
            },
            "nested": {
                "depends": [],
                "files": [{"source": "nested/dir/.config", "target": "~/.config/test"}],
                "variables": {},
            },
        },
    }

    local_config = {
        "packages": ["bash", "vim"],
        "variables": {"local_var": "local_value"},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    return repo_dir


@pytest.fixture
def repo_with_source_files(repo_with_packages):
    """Create source files for the packages in the repo."""
    repo_dir = repo_with_packages

    (repo_dir / "bash").mkdir()
    (repo_dir / "bash/.bashrc").write_text("# Bashrc content\n")

    (repo_dir / "vim").mkdir()
    (repo_dir / "vim/.vimrc").write_text("# Vimrc content\n")

    (repo_dir / "zsh").mkdir()
    (repo_dir / "zsh/.zshrc").write_text("# Zshrc content\n")

    (repo_dir / "nested" / "dir").mkdir(parents=True)
    (repo_dir / "nested" / "dir" / ".config").write_text("# Config content\n")

    return repo_dir


@pytest.fixture
def repo_with_circular_dependency(temp_repo):
    """Create a repo with circular dependencies."""
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
            "pkg_a": {
                "depends": ["pkg_b"],
                "files": [{"source": "a/file", "target": "~/.a"}],
                "variables": {},
            },
            "pkg_b": {
                "depends": ["pkg_a"],
                "files": [{"source": "b/file", "target": "~/.b"}],
                "variables": {},
            },
        },
    }

    local_config = {
        "packages": ["pkg_a", "pkg_b"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    return repo_dir


@pytest.fixture
def repo_with_missing_source(repo_with_packages):
    """Create a repo where some source files are missing."""
    repo_dir = repo_with_packages

    (repo_dir / "bash").mkdir()
    (repo_dir / "bash/.bashrc").write_text("# Bashrc content\n")

    (repo_dir / "vim").mkdir()
    (repo_dir / "vim/.vimrc").write_text("# Vimrc content\n")

    return repo_dir


@pytest.fixture
def home_dir(tmp_path):
    """Create a temporary home directory."""
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def env_with_home(home_dir, monkeypatch):
    """Set up environment with temporary home directory."""
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")


@pytest.fixture
def deployed_repo(repo_with_source_files, home_dir, monkeypatch):
    """Create a repo with deployed symlinks for absorb tests."""
    repo_dir = repo_with_source_files

    bashrc_link = home_dir / ".bashrc"
    bashrc_link.parent.mkdir(parents=True, exist_ok=True)
    bashrc_link.symlink_to(repo_dir / "bash" / ".bashrc")

    return repo_dir


@pytest.fixture
def deployed_repo_with_symlink(repo_with_packages, home_dir, monkeypatch):
    """Create a repo where target directory has a symlink."""
    repo_dir = repo_with_packages

    bash_dir = repo_dir / "bash"
    bash_dir.mkdir()
    (bash_dir / ".bashrc").write_text("# bashrc content\n")

    vim_dir = repo_dir / "vim"
    vim_dir.mkdir()
    (vim_dir / ".vimrc").write_text("# vimrc content\n")

    bashrc_link = home_dir / ".bashrc"
    bashrc_link.parent.mkdir(parents=True, exist_ok=True)
    bashrc_link.symlink_to(bash_dir / ".bashrc")

    return repo_dir


@pytest.fixture
def deployed_repo_with_template(repo_with_packages, home_dir, monkeypatch):
    """Create a repo with template files for absorb tests."""
    repo_dir = repo_with_packages

    bash_dir = repo_dir / "bash"
    bash_dir.mkdir()
    (bash_dir / ".bashrc.j2").write_text("# Template for {{ user }}\n")

    bashrc_file = home_dir / ".bashrc"
    bashrc_file.parent.mkdir(parents=True, exist_ok=True)
    bashrc_file.write_text("# rendered content\n")

    return repo_dir


@pytest.fixture
def deployed_repo_with_ignore_pattern(temp_repo, home_dir, monkeypatch):
    """Create a repo with absorb_ignore patterns for absorb tests."""
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
                "files": [
                    {
                        "source": "config/dir",
                        "target": "~/.config_ignore",
                        "absorb_ignore": [".*\\.swp", ".*\\.bak"],
                    }
                ],
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
    (config_dir / "file1.swp").write_text("# swap\n")
    (config_dir / "file2.bak").write_text("# backup\n")

    config_home = home_dir / ".config_ignore"
    config_home.mkdir(parents=True)
    (config_home / "file1").write_text("# modified file1\n")
    (config_home / "file1.swp").write_text("# modified swap\n")
    (config_home / "file2.bak").write_text("# modified backup\n")

    return repo_dir


@pytest.fixture
def deployed_repo_with_symlinks(repo_with_source_files, home_dir, monkeypatch):
    """Create a repo with deployed symlinks for undeploy tests."""
    repo_dir = repo_with_source_files

    bashrc_link = home_dir / ".bashrc"
    bashrc_link.parent.mkdir(parents=True, exist_ok=True)
    bashrc_link.symlink_to(repo_dir / "bash" / ".bashrc")

    vimrc_link = home_dir / ".vimrc"
    vimrc_link.parent.mkdir(parents=True, exist_ok=True)
    vimrc_link.symlink_to(repo_dir / "vim" / ".vimrc")

    return repo_dir


@pytest.fixture
def deployed_repo_with_regular_files(repo_with_source_files, home_dir, monkeypatch):
    """Create a repo where target files are regular files (not symlinks)."""
    repo_dir = repo_with_source_files

    bashrc_file = home_dir / ".bashrc"
    bashrc_file.parent.mkdir(parents=True, exist_ok=True)
    bashrc_file.write_text("# Regular file content\n")

    vimrc_file = home_dir / ".vimrc"
    vimrc_file.parent.mkdir(parents=True, exist_ok=True)
    vimrc_file.write_text("# Vimrc regular file\n")

    return repo_dir


@pytest.fixture
def deployed_repo_with_circular_dep(
    repo_with_circular_dependency, home_dir, monkeypatch
):
    """Create a repo with circular dependencies that are deployed."""
    repo_dir = repo_with_circular_dependency

    a_dir = repo_dir / "a"
    a_dir.mkdir()
    (a_dir / "file").write_text("# file a\n")

    b_dir = repo_dir / "b"
    b_dir.mkdir()
    (b_dir / "file").write_text("# file b\n")

    a_link = home_dir / ".a"
    a_link.parent.mkdir(parents=True, exist_ok=True)
    a_link.symlink_to(a_dir / "file")

    b_link = home_dir / ".b"
    b_link.parent.mkdir(parents=True, exist_ok=True)
    b_link.symlink_to(b_dir / "file")

    return repo_dir


@pytest.fixture
def temp_repo_with_missing_dep(temp_repo):
    """Create a temp repo where a dependency is not defined."""
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
            "pkg_a": {
                "depends": ["pkg_b"],
                "files": [{"source": "a/file", "target": "~/.a"}],
                "variables": {},
            },
        },
    }

    local_config = {
        "packages": ["pkg_a"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    a_dir = repo_dir / "a"
    a_dir.mkdir()
    (a_dir / "file").write_text("# file a\n")

    return repo_dir


@pytest.fixture
def temp_repo_with_disabled_dep(temp_repo):
    """Create a temp repo where a dependency is not enabled."""
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
            "pkg_a": {
                "depends": ["pkg_b"],
                "files": [{"source": "a/file", "target": "~/.a"}],
                "variables": {},
            },
            "pkg_b": {
                "depends": [],
                "files": [{"source": "b/file", "target": "~/.b"}],
                "variables": {},
            },
        },
    }

    local_config = {
        "packages": ["pkg_a"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    a_dir = repo_dir / "a"
    a_dir.mkdir()
    (a_dir / "file").write_text("# file a\n")

    b_dir = repo_dir / "b"
    b_dir.mkdir()
    (b_dir / "file").write_text("# file b\n")

    return repo_dir


@pytest.fixture
def deployed_repo_with_multiple_symlinks(repo_with_source_files, home_dir, monkeypatch):
    """Create a repo with multiple packages deployed as symlinks."""
    repo_dir = repo_with_source_files

    bashrc_link = home_dir / ".bashrc"
    bashrc_link.parent.mkdir(parents=True, exist_ok=True)
    bashrc_link.symlink_to(repo_dir / "bash" / ".bashrc")

    vimrc_link = home_dir / ".vimrc"
    vimrc_link.parent.mkdir(parents=True, exist_ok=True)
    vimrc_link.symlink_to(repo_dir / "vim" / ".vimrc")

    zshrc_link = home_dir / ".zshrc"
    zshrc_link.parent.mkdir(parents=True, exist_ok=True)
    zshrc_link.symlink_to(repo_dir / "zsh" / ".zshrc")

    return repo_dir


@pytest.fixture
def temp_repo_with_simple_package(temp_repo):
    """Create a temp repo with a simple single package for testing."""
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
            "simple": {
                "depends": [],
                "files": [{"source": "simple/file", "target": "~/.simple"}],
                "variables": {},
            },
        },
    }

    local_config = {
        "packages": ["simple"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    simple_dir = repo_dir / "simple"
    simple_dir.mkdir()
    (simple_dir / "file").write_text("# simple file\n")

    return repo_dir


@pytest.fixture
def git_repo(temp_repo, monkeypatch):
    """Create a git repository in the temp repo."""
    import subprocess

    monkeypatch.chdir(temp_repo)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], check=True, capture_output=True
    )

    remote_dir = temp_repo.parent / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote_dir)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_dir)],
        check=True,
        capture_output=True,
    )

    (temp_repo / "README.md").write_text("# Test Repository\n")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], check=True, capture_output=True
    )

    subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=temp_repo,
        capture_output=True,
    )

    return temp_repo


@pytest.fixture
def git_repo_with_remote(git_repo, tmp_path, monkeypatch):
    """Create a git repository with a bare remote repository."""
    import subprocess

    remote_dir = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote_dir)], check=True, capture_output=True
    )

    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_dir)],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

    push_result = subprocess.run(
        ["git", "push", "-u", "origin", current_branch],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    if push_result.returncode != 0:
        subprocess.run(
            ["git", "push", "-f", "-u", "origin", current_branch],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

    return git_repo


@pytest.fixture
def git_repo_with_changes(git_repo_with_remote, monkeypatch):
    """Create a git repo with uncommitted changes."""
    import subprocess

    monkeypatch.chdir(git_repo_with_remote)
    (git_repo_with_remote / "new_file.txt").write_text("# New file content\n")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)

    return git_repo_with_remote


@pytest.fixture
def git_repo_with_unstaged_changes(git_repo_with_remote, monkeypatch):
    """Create a git repo with unstaged changes (not added)."""

    monkeypatch.chdir(git_repo_with_remote)
    (git_repo_with_remote / "unstaged_file.txt").write_text("# Unstaged content\n")

    return git_repo_with_remote


@pytest.fixture
def repo_with_doctor_config(temp_repo, home_dir, monkeypatch):
    """Create a temp repo with packages that have doctor config."""
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
            "pkg_with_executables": {
                "depends": [],
                "files": [{"source": "pkg/file", "target": "~/.pkg"}],
                "variables": {},
                "doctor": {
                    "executables": [
                        {"name": "python3", "severity": "error"},
                        {"name": "nonexistent_command_xyz", "severity": "error"},
                    ]
                },
            },
        },
    }

    local_config = {
        "packages": ["pkg_with_executables"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    pkg_dir = repo_dir / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "file").write_text("# pkg file\n")

    return repo_dir


@pytest.fixture
def repo_with_doctor_warning_only(temp_repo, home_dir, monkeypatch):
    """Create a temp repo with packages that have only warning severity."""
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
            "pkg_with_warning": {
                "depends": [],
                "files": [{"source": "pkg/file", "target": "~/.pkg"}],
                "variables": {},
                "doctor": {
                    "executables": [
                        {"name": "nonexistent_command_xyz", "severity": "warning"},
                    ]
                },
            },
        },
    }

    local_config = {
        "packages": ["pkg_with_warning"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    pkg_dir = repo_dir / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "file").write_text("# pkg file\n")

    return repo_dir


@pytest.fixture
def repo_with_doctor_config_and_deps(temp_repo, home_dir, monkeypatch):
    """Create a temp repo with packages that have doctor config and dependencies."""
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
            "parent": {
                "depends": ["child"],
                "files": [{"source": "parent/file", "target": "~/.parent"}],
                "variables": {},
                "doctor": {
                    "executables": [
                        {"name": "python3", "severity": "error"},
                    ]
                },
            },
            "child": {
                "depends": [],
                "files": [{"source": "child/file", "target": "~/.child"}],
                "variables": {},
                "doctor": {
                    "executables": [
                        {"name": "git", "severity": "error"},
                    ]
                },
            },
        },
    }

    local_config = {
        "packages": ["parent"],
        "variables": {},
        "file_overrides": {},
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    with open(local_config_path, "w") as f:
        yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

    parent_dir = repo_dir / "parent"
    parent_dir.mkdir()
    (parent_dir / "file").write_text("# parent file\n")

    child_dir = repo_dir / "child"
    child_dir.mkdir()
    (child_dir / "file").write_text("# child file\n")

    return repo_dir
