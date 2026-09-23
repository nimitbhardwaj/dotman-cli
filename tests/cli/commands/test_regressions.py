"""Regression tests for bugs found in the 2026-09 audit."""

import subprocess

import pytest
import yaml

from dotman.cli import app
from dotman.managers import RemoteManager


@pytest.fixture
def repo(tmp_path, runner, monkeypatch):
    """A dotman repo with one package, HOME redirected to tmp."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTMAN_CONFIG_DIR", "")
    repo_dir = tmp_path / "repo"
    (repo_dir / ".dotman").mkdir(parents=True)
    monkeypatch.chdir(repo_dir)

    def write(files, settings=None):
        config = {
            "variables": {"name": "nimit"},
            "settings": settings or {},
            "packages": {"app": {"files": files}},
        }
        (repo_dir / ".dotman/config.yaml").write_text(yaml.dump(config))
        (repo_dir / ".dotman/local.yaml").write_text("packages: [app]\n")

    return repo_dir, home, write


def test_single_file_template_with_extension_shows_synced(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "app.toml.j2").write_text("name={{ name }}\n")
    write([{"source": "app.toml.j2", "target": "~/.config/app.toml"}])

    assert runner.invoke(app, ["deploy"]).exit_code == 0
    assert (home / ".config/app.toml").read_text() == "name=nimit\n"
    result = runner.invoke(app, ["status"])
    assert "Synced" in result.output


def test_template_deploy_backs_up_existing_file(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "rc.j2").write_text("name={{ name }}\n")
    write([{"source": "rc.j2", "target": "~/.rc"}])
    (home / ".rc").write_text("precious\n")

    assert runner.invoke(app, ["deploy"]).exit_code == 0
    backups = list((repo_dir / ".dotman/backups").iterdir())
    assert [b.read_text() for b in backups] == ["precious\n"]


def test_template_never_writes_through_symlink_into_repo(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "rc").write_text("original\n")
    (repo_dir / "rc.j2").write_text("name={{ name }}\n")
    (home / ".rc").symlink_to(repo_dir / "rc")
    write([{"source": "rc.j2", "target": "~/.rc"}])

    assert runner.invoke(app, ["deploy"]).exit_code == 0
    assert (repo_dir / "rc").read_text() == "original\n"
    assert not (home / ".rc").is_symlink()


def test_deploy_exits_nonzero_on_conflict(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "rc").write_text("x\n")
    (home / ".rc").write_text("user file\n")
    write([{"source": "rc", "target": "~/.rc"}])

    assert runner.invoke(app, ["deploy"]).exit_code == 1


def test_rollback_keeps_user_file_that_replaced_symlink(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "rc").write_text("x\n")
    write([{"source": "rc", "target": "~/.rc"}])
    assert runner.invoke(app, ["deploy"]).exit_code == 0

    (home / ".rc").unlink()
    (home / ".rc").write_text("user edited\n")
    runner.invoke(app, ["rollback"])
    assert (home / ".rc").read_text() == "user edited\n"


def test_settings_backup_dir_is_honoured(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "rc").write_text("x\n")
    (home / ".rc").write_text("old\n")
    write([{"source": "rc", "target": "~/.rc"}], {"backup_dir": "my-backups"})

    assert runner.invoke(app, ["deploy", "--force"]).exit_code == 0
    assert len(list((repo_dir / "my-backups").iterdir())) == 1


def test_absorb_ignore_accepts_glob_patterns(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "cfg").mkdir()
    (home / ".cfg/.git").mkdir(parents=True)
    (home / ".cfg/.git/HEAD").write_text("ref\n")
    (home / ".cfg/debug.log").write_text("log\n")
    (home / ".cfg/keep.conf").write_text("keep\n")
    files = [
        {"source": "cfg", "target": "~/.cfg", "absorb_ignore": ["*.log", ".git/**"]}
    ]
    write(files)

    result = runner.invoke(app, ["absorb"])
    assert result.exit_code == 0, result.output
    assert (repo_dir / "cfg/keep.conf").exists()
    assert not (repo_dir / "cfg/debug.log").exists()
    assert not (repo_dir / "cfg/.git").exists()


def test_has_changes_sees_untracked_files(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    manager = RemoteManager(tmp_path)
    assert not manager.has_changes()
    (tmp_path / "new_dotfile").write_text("x\n")
    assert manager.has_changes()


def test_diff_shows_template_drift(runner, repo):
    repo_dir, home, write = repo
    (repo_dir / "rc.j2").write_text("name={{ name }}\n")
    write([{"source": "rc.j2", "target": "~/.rc"}])
    runner.invoke(app, ["deploy"])
    assert runner.invoke(app, ["diff"]).exit_code == 0

    (home / ".rc").write_text("name=someone-else\n")
    result = runner.invoke(app, ["diff"])
    assert result.exit_code == 1
    assert "+name=nimit" in result.output
