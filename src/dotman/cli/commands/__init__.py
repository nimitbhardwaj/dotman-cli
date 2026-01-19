"""CLI commands subpackage."""

from dotman.cli.commands import history as history_mod
from dotman.cli.commands.absorb import absorb_changes
from dotman.cli.commands.clone import clone
from dotman.cli.commands.deploy import deploy, undeploy
from dotman.cli.commands.init import init
from dotman.cli.commands.pull import pull
from dotman.cli.commands.push import push
from dotman.cli.commands.repo import (
    add_repository,
    list_repositories,
    remove_repository,
    set_default_repository,
    show_repository,
)
from dotman.cli.commands.status import list_packages, status
from dotman.cli.commands.watch import watch

history = history_mod.history
rollback = history_mod.rollback

__all__ = [
    "absorb_changes",
    "add_repository",
    "clone",
    "deploy",
    "history",
    "init",
    "list_packages",
    "list_repositories",
    "pull",
    "push",
    "remove_repository",
    "rollback",
    "set_default_repository",
    "show_repository",
    "status",
    "undeploy",
    "watch",
]
