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
