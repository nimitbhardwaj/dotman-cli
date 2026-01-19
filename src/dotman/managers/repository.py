"""Repository management for multiple dotfiles repositories."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from dotman.core.exceptions import (
    ConfigNotFoundError,
    ConfigParseError,
    RepositoryNotFoundError,
)


class RepositoryConfig(BaseModel):
    """Configuration for a single dotfiles repository."""

    name: str
    path: Path
    remote_url: str | None = None
    description: str | None = None
    is_default: bool = False


class RepositoryRegistry(BaseModel):
    """Registry of all configured dotfiles repositories."""

    repositories: dict[str, RepositoryConfig] = Field(default_factory=dict)
    default_repo: str | None = None

    def add_repository(self, repo: RepositoryConfig) -> None:
        """Add a repository to the registry."""
        self.repositories[repo.name] = repo
        if repo.is_default or self.default_repo is None:
            self.default_repo = repo.name

    def remove_repository(self, name: str) -> RepositoryConfig | None:
        """Remove a repository from the registry."""
        return self.repositories.pop(name, None)

    def get_repository(self, name: str) -> RepositoryConfig | None:
        """Get a repository by name."""
        return self.repositories.get(name)

    def get_default_repository(self) -> RepositoryConfig | None:
        """Get the default repository."""
        if self.default_repo:
            return self.repositories.get(self.default_repo)
        if self.repositories:
            return next(iter(self.repositories.values()))
        return None

    def set_default(self, name: str) -> None:
        """Set the default repository."""
        if name in self.repositories:
            self.default_repo = name
            self.repositories[name].is_default = True


class RepoManager:
    """Manages multiple dotfiles repositories."""

    REGISTRY_FILENAME = "repos.yaml"

    def __init__(self, registry_dir: Path | None = None):
        """Initialize the repository manager.

        Args:
            registry_dir: Directory containing the repository registry.
            Defaults to ~/.config/dotman/
        """
        if registry_dir is None:
            registry_dir = Path.home() / ".config" / "dotman"
        self.registry_dir = registry_dir
        self.registry_path = self.registry_dir / self.REGISTRY_FILENAME
        self._registry: RepositoryRegistry | None = None

    @property
    def registry(self) -> RepositoryRegistry:
        """Load and return the repository registry."""
        if self._registry is None:
            self._registry = self._load_registry()
        return self._registry

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a YAML file and return its contents."""
        if not path.exists():
            return {}

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except yaml.YAMLError as e:
            raise ConfigParseError(f"Error parsing {path}: {e}") from e

    def _load_registry(self) -> RepositoryRegistry:
        """Load the repository registry."""
        try:
            data = self._load_yaml(self.registry_path)
            return RepositoryRegistry(**data)
        except ConfigNotFoundError:
            return RepositoryRegistry()

    def _save_registry(self) -> None:
        """Save the repository registry to disk."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            yaml.dump(
                self.registry.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    def register_repository(
        self,
        name: str,
        path: Path,
        remote_url: str | None = None,
        description: str | None = None,
        set_default: bool = False,
    ) -> RepositoryConfig:
        """Register a dotfiles repository.

        Args:
            name: Unique name for the repository
            path: Path to the repository directory
            remote_url: Optional remote URL
            description: Optional description
            set_default: Whether to set as the default repository

        Returns:
            The created RepositoryConfig
        """
        path = Path(path).resolve()
        repo = RepositoryConfig(
            name=name,
            path=path,
            remote_url=remote_url,
            description=description,
            is_default=set_default,
        )

        if set_default:
            for existing_name, existing_repo in self.registry.repositories.items():
                existing_repo.is_default = False

        self.registry.add_repository(repo)
        self._save_registry()
        return repo

    def unregister_repository(self, name: str) -> bool:
        """Unregister a dotfiles repository.

        Args:
            name: Name of the repository to unregister

        Returns:
            True if the repository was found and removed
        """
        repo = self.registry.remove_repository(name)
        if repo:
            if self.registry.default_repo == name:
                self.registry.default_repo = None
                if self.registry.repositories:
                    new_default = next(iter(self.registry.repositories.values()))
                    new_default.is_default = True
                    self.registry.default_repo = new_default.name
            self._save_registry()
            return True
        return False

    def get_repository(self, name: str | None) -> RepositoryConfig:
        """Get a repository by name or the default.

        Args:
            name: Repository name or None for default

        Returns:
            The RepositoryConfig

        Raises:
            RepositoryNotFoundError: If the repository is not found
        """
        if name is None:
            repo = self.registry.get_default_repository()
            if repo is None:
                raise RepositoryNotFoundError(
                    "No default repository set. "
                    "Use 'dotman repo add' to add a repository."
                )
            return repo

        repo = self.registry.get_repository(name)
        if repo is None:
            raise RepositoryNotFoundError(
                f"Repository '{name}' not found. "
                f"Use 'dotman repo list' to see available repositories."
            )
        return repo

    def list_repositories(self) -> list[RepositoryConfig]:
        """List all registered repositories."""
        return list(self.registry.repositories.values())

    def set_default_repository(self, name: str) -> bool:
        """Set the default repository.

        Args:
            name: Name of the repository to set as default

        Returns:
            True if successful
        """
        if name not in self.registry.repositories:
            return False

        for existing_name, existing_repo in self.registry.repositories.items():
            existing_repo.is_default = existing_name == name

        self.registry.default_repo = name
        self._save_registry()
        return True

    def get_registry_path(self) -> Path:
        """Get the path to the registry file."""
        return self.registry_path

    def is_repository(self, path: Path) -> bool:
        """Check if a path is a registered dotman repository."""
        path = Path(path).resolve()
        for repo in self.registry.repositories.values():
            if repo.path.resolve() == path:
                return True
        return False

    def find_repository_by_path(self, path: Path) -> RepositoryConfig | None:
        """Find a repository by its path.

        Args:
            path: The path to search for

        Returns:
            RepositoryConfig if found, None otherwise
        """
        path = Path(path).resolve()
        for repo in self.registry.repositories.values():
            if repo.path.resolve() == path:
                return repo
        return None
