"""Deployment history tracking for Dotman."""

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from dotman.exceptions import HistoryError


@dataclass
class DeployedFile:
    """Represents a single file deployed in a deployment session."""

    source: str
    target: str
    is_template: bool = False
    backup_path: str | None = None


@dataclass
class DeploymentRecord:
    """A record of a single deployment session."""

    timestamp: str
    deployment_id: str
    packages: list[str]
    files: list[DeployedFile]
    dry_run: bool = False


@dataclass
class DeploymentHistory:
    """The complete deployment history."""

    deployments: list[DeploymentRecord] = field(default_factory=list)


class HistoryManager:
    """Manages deployment history in .dotman/history.yaml."""

    def __init__(self, dotman_dir: Path):
        self.dotman_dir = dotman_dir
        self.history_path = dotman_dir / "history.yaml"
        self._history: DeploymentHistory | None = None

    @property
    def history(self) -> DeploymentHistory:
        """Load and return the deployment history."""
        if self._history is None:
            self._history = self._load_history()
        return self._history

    def _load_history(self) -> DeploymentHistory:
        """Load history from file or return empty history."""
        if not self.history_path.exists():
            return DeploymentHistory()

        try:
            with open(self.history_path) as f:
                data = yaml.safe_load(f) or {}
                return self._parse_history(data)
        except yaml.YAMLError as e:
            raise HistoryError(f"Error parsing history file: {e}") from e

    def _parse_history(self, data: dict[str, Any]) -> DeploymentHistory:
        """Parse YAML data into DeploymentHistory."""
        deployments = []
        for dep_data in data.get("deployments", []):
            files = [
                DeployedFile(
                    source=f.get("source", ""),
                    target=f.get("target", ""),
                    is_template=f.get("is_template", False),
                    backup_path=f.get("backup_path"),
                )
                for f in dep_data.get("files", [])
            ]
            deployments.append(
                DeploymentRecord(
                    timestamp=dep_data.get("timestamp", ""),
                    deployment_id=dep_data.get("deployment_id", ""),
                    packages=dep_data.get("packages", []),
                    files=files,
                    dry_run=dep_data.get("dry_run", False),
                )
            )
        return DeploymentHistory(deployments=deployments)

    def save_history(self) -> None:
        """Save the current history to file."""
        self.dotman_dir.mkdir(parents=True, exist_ok=True)
        data = self._serialize_history(self.history)
        with open(self.history_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def _serialize_history(self, history: DeploymentHistory) -> dict[str, Any]:
        """Serialize history to YAML-serializable format."""
        return {
            "deployments": [
                {
                    "timestamp": dep.timestamp,
                    "deployment_id": dep.deployment_id,
                    "packages": dep.packages,
                    "files": [
                        {
                            "source": f.source,
                            "target": f.target,
                            "is_template": f.is_template,
                            "backup_path": f.backup_path,
                        }
                        for f in dep.files
                    ],
                    "dry_run": dep.dry_run,
                }
                for dep in history.deployments
            ]
        }

    def add_deployment(
        self,
        deployment_id: str,
        packages: list[str],
        files: list[DeployedFile],
        dry_run: bool = False,
    ) -> None:
        """Add a new deployment record to history."""
        record = DeploymentRecord(
            timestamp=datetime.now().isoformat(),
            deployment_id=deployment_id,
            packages=packages,
            files=files,
            dry_run=dry_run,
        )
        self.history.deployments.append(record)
        if not dry_run:
            self.save_history()

    def get_deployment(self, deployment_id: str) -> DeploymentRecord | None:
        """Get a specific deployment by ID."""
        for dep in self.history.deployments:
            if dep.deployment_id == deployment_id:
                return dep
        return None

    def get_latest_deployment(self) -> DeploymentRecord | None:
        """Get the most recent deployment record."""
        if self.history.deployments:
            return self.history.deployments[-1]
        return None

    def get_deployments(self, limit: int | None = None) -> list[DeploymentRecord]:
        """Get all deployments, optionally limited to recent ones."""
        if limit:
            return self.history.deployments[-limit:]
        return self.history.deployments

    def remove_deployment(self, deployment_id: str) -> bool:
        """Remove a deployment from history. Returns True if found and removed."""
        for i, dep in enumerate(self.history.deployments):
            if dep.deployment_id == deployment_id:
                self.history.deployments.pop(i)
                self.save_history()
                return True
        return False

    def clear_history(self) -> None:
        """Clear all deployment history."""
        self.history.deployments.clear()
        self.save_history()

    def restore_from_backup(
        self, backup_path: Path, target_path: Path, dry_run: bool = False
    ) -> bool:
        """Restore a file from backup to target location.

        Args:
            backup_path: Path to the backup file
            target_path: Path where the file should be restored
            dry_run: If True, only simulate the restoration

        Returns:
            True if restoration was successful, False otherwise
        """
        if not backup_path.exists():
            return False

        if dry_run:
            return True

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(backup_path), str(target_path))
        return True

    def cleanup_backup(self, backup_path: Path, dry_run: bool = False) -> None:
        """Remove a backup file after successful restoration."""
        if backup_path.exists():
            if not dry_run:
                backup_path.unlink()
            elif backup_path.exists():
                backup_path.unlink()
