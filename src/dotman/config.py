"""Configuration management for Dotman."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from dotman.exceptions import (
    CircularDependencyError,
    ConfigNotFoundError,
    ConfigParseError,
    MissingDependencyError,
)
from dotman.repository import RepoManager, RepositoryConfig


class FileMapping(BaseModel):
    """A single file mapping configuration.

    Templates are automatically detected by .j2 extension.
    """

    source: str
    target: str
    absorb_ignore: list[str] = Field(default_factory=list)


class HookConfig(BaseModel):
    """Configuration for package hooks."""

    pre_deploy: list[str] = Field(default_factory=list)
    post_deploy: list[str] = Field(default_factory=list)


class PackageConfig(BaseModel):
    """Configuration for a single package."""

    depends: list[str] = Field(default_factory=list)
    files: list[FileMapping] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    hooks: HookConfig = Field(default_factory=HookConfig)


class GlobalSettings(BaseModel):
    """Global settings from global.yaml."""

    backup_dir: str = ".dotman/backups"
    template_suffix: str = ".j2"


class GlobalConfig(BaseModel):
    """Global configuration structure."""

    settings: GlobalSettings = Field(default_factory=GlobalSettings)
    variables: dict[str, Any] = Field(default_factory=dict)
    packages: dict[str, PackageConfig] = Field(default_factory=dict)


class LocalConfig(BaseModel):
    """Local configuration structure."""

    packages: list[str] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    file_overrides: dict[str, dict[str, str]] = Field(default_factory=dict)


def get_repo_manager(registry_dir: Path | None = None) -> RepoManager:
    """Get the repository manager instance.

    Args:
        registry_dir: Optional custom registry directory

    Returns:
        RepoManager instance
    """
    return RepoManager(registry_dir)


def get_config_for_repo(
    repo_name: str | None = None, registry_dir: Path | None = None
) -> tuple["Config", RepositoryConfig]:
    """Get a Config instance for a specific repository.

    Args:
        repo_name: Repository name or None for default repository
        registry_dir: Optional custom registry directory

    Returns:
        Tuple of (Config, RepositoryConfig)

    Raises:
        RepositoryNotFoundError: If the repository is not found
    """
    repo_manager = get_repo_manager(registry_dir)
    repo_config = repo_manager.get_repository(repo_name)
    return Config(repo_config.path), repo_config


class Config:
    """Main configuration class that merges global and local configs."""

    def __init__(self, repo_dir: Path | None = None, repo_name: str | None = None):
        """Initialize config for a dotfiles repository.

        Args:
            repo_dir: The dotfiles repository directory.
            Defaults to current working directory.
                      Config files are stored in repo_dir/.dotman/
            repo_name: Optional name of the repository (for display purposes)
        """
        self.repo_dir = repo_dir or Path.cwd()
        self.repo_name = repo_name
        self.dotman_dir = self.repo_dir / ".dotman"
        self.config_path = self.dotman_dir / "config.yaml"
        self.local_config_path = self.dotman_dir / "local.yaml"
        self._global_config: GlobalConfig | None = None
        self._local_config: LocalConfig | None = None

    @property
    def global_config(self) -> GlobalConfig:
        """Load and return global configuration."""
        if self._global_config is None:
            self._global_config = self._load_global_config()
        return self._global_config

    @property
    def local_config(self) -> LocalConfig:
        """Load and return local configuration."""
        if self._local_config is None:
            self._local_config = self._load_local_config()
        return self._local_config

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a YAML file and return its contents."""
        if not path.exists():
            raise ConfigNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except yaml.YAMLError as e:
            raise ConfigParseError(f"Error parsing {path}: {e}") from e

    def _load_global_config(self) -> GlobalConfig:
        """Load the global configuration."""
        try:
            data = self._load_yaml(self.config_path)
            return GlobalConfig(**data)
        except ConfigNotFoundError:
            return GlobalConfig()

    def _load_local_config(self) -> LocalConfig:
        """Load the local configuration."""
        try:
            data = self._load_yaml(self.local_config_path)
            return LocalConfig(**data)
        except ConfigNotFoundError:
            return LocalConfig()

    @property
    def settings(self) -> GlobalSettings:
        """Get global settings."""
        return self.global_config.settings

    @property
    def dotfiles_dir(self) -> Path:
        """Get the dotfiles directory path (the repo itself)."""
        return self.repo_dir

    @property
    def backup_dir(self) -> Path:
        """Get the backup directory path."""
        return self.dotman_dir / "backups"

    def get_enabled_packages(self) -> list[str]:
        """Get list of packages enabled in local config."""
        return self.local_config.packages

    def get_package(self, name: str) -> PackageConfig | None:
        """Get a package configuration by name."""
        return self.global_config.packages.get(name)

    def validate_dependencies(self, package_names: list[str] | None = None) -> None:
        """Validate that all dependencies are defined in config
        and enabled in local.yaml.

        Args:
            package_names: List of package names to validate.
            If None, validates all enabled packages.

        Raises:
            MissingDependencyError: If a dependency is missing from config
            or not enabled in local.yaml.
        """
        packages_to_validate = package_names or self.get_enabled_packages()
        enabled_packages = set(packages_to_validate)
        defined_packages = set(self.global_config.packages.keys())

        # First, check that all requested packages exist in config
        for pkg_name in packages_to_validate:
            if pkg_name not in defined_packages:
                raise MissingDependencyError(
                    f"Package '{pkg_name}' is enabled in local.yaml but"
                    f" not defined in config.yaml.\n"
                    f"Add it to the packages section in config.yaml,"
                    f" or remove it from local.yaml."
                )

        # Then validate dependencies recursively
        def validate_recursive(
            pkg_name: str, validated: set[str], visiting: set[str]
        ) -> None:
            if pkg_name in validated:
                return

            # Detect circular dependency
            if pkg_name in visiting:
                path = " -> ".join(visiting) + " -> " + pkg_name
                raise CircularDependencyError(f"Circular dependency detected: {path}")

            visiting.add(pkg_name)

            package = self.get_package(pkg_name)
            if not package:
                visiting.remove(pkg_name)
                return  # Already checked above

            for dep in package.depends:
                # Check if dependency is defined in config
                if dep not in defined_packages:
                    visiting.remove(pkg_name)
                    raise MissingDependencyError(
                        f"Package '{pkg_name}' depends on '{dep}',"
                        f" but '{dep}' is not defined in config.yaml.\n"
                        f"Define '{dep}' in config.yaml's packages section."
                    )
                # Check if dependency is enabled in local.yaml
                if dep not in enabled_packages:
                    visiting.remove(pkg_name)
                    raise MissingDependencyError(
                        f"Package '{pkg_name}' depends on '{dep}',"
                        f" but '{dep}' is not enabled in local.yaml.\n"
                        f"Add '{dep}' to the packages list in local.yaml."
                    )
                # Recursively validate the dependency
                validate_recursive(dep, validated, visiting)

            visiting.remove(pkg_name)
            validated.add(pkg_name)

        for pkg_name in packages_to_validate:
            validate_recursive(pkg_name, set(), set())

    def get_all_packages_with_dependencies(
        self, package_names: list[str] | None = None
    ) -> list[str]:
        """Get list of packages including all their dependencies.

        Args:
            package_names: List of package names. If None, uses all enabled packages.

        Returns:
            List of package names including all dependencies (topologically sorted).

        Raises:
            MissingDependencyError: If a dependency is missing or not enabled.
        """
        packages_to_process = package_names or self.get_enabled_packages()

        # Validate dependencies first
        self.validate_dependencies(packages_to_process)

        # Collect all packages with their dependencies
        result = []
        processed = set()

        def add_with_deps(pkg_name: str) -> None:
            if pkg_name in processed:
                return
            package = self.get_package(pkg_name)
            if package:
                for dep in package.depends:
                    add_with_deps(dep)
                if pkg_name not in processed:
                    result.append(pkg_name)
                    processed.add(pkg_name)

        for pkg_name in packages_to_process:
            add_with_deps(pkg_name)

        return result

    def get_packages_in_deployment_order(
        self, package_names: list[str] | None = None
    ) -> list[str]:
        """Get packages in correct deployment order using topological sort.

        Dependencies are deployed before packages that depend on them.
        Maintains relative order of explicitly specified packages when possible.

        Args:
            package_names: List of package names. If None, uses all enabled packages.

        Returns:
            List of package names in deployment order (dependencies first).

        Raises:
            CircularDependencyError: If circular dependencies are detected.
            MissingDependencyError: If a dependency is missing or not enabled.
        """
        packages_to_deploy = package_names or self.get_enabled_packages()

        all_packages = self.get_all_packages_with_dependencies(packages_to_deploy)

        dependency_graph: dict[str, set[str]] = {}
        in_degree: dict[str, int] = {}

        for pkg_name in all_packages:
            package = self.get_package(pkg_name)
            deps = package.depends if package else []
            dependency_graph[pkg_name] = set(deps)
            in_degree[pkg_name] = len(deps)

        from collections import deque

        queue = deque([pkg for pkg in all_packages if in_degree[pkg] == 0])
        deployment_order = []

        while queue:
            current = queue.popleft()
            deployment_order.append(current)

            for dependent_pkg, pkg_deps in dependency_graph.items():
                if current in pkg_deps:
                    in_degree[dependent_pkg] -= 1
                    if in_degree[dependent_pkg] == 0:
                        queue.append(dependent_pkg)

        remaining = [pkg for pkg in all_packages if in_degree[pkg] > 0]
        if remaining:
            cycle_path = " -> ".join(remaining) + " -> " + remaining[0]
            raise CircularDependencyError(f"Circular dependency detected: {cycle_path}")

        return deployment_order

    def get_packages_in_undeployment_order(
        self, package_names: list[str] | None = None
    ) -> list[str]:
        """Get packages in correct undeployment order (reverse of deployment).

        Args:
            package_names: List of package names. If None, uses all enabled packages.

        Returns:
            List of package names in undeployment order (dependents first).
        """
        deployment_order = self.get_packages_in_deployment_order(package_names)
        return list(reversed(deployment_order))

    def get_merged_variables(self, package_name: str | None = None) -> dict[str, Any]:
        """Get merged variables from global, local, and package configs."""
        variables = dict(self.global_config.variables)
        variables.update(self.local_config.variables)

        if package_name:
            package = self.get_package(package_name)
            if package:
                variables.update(package.variables)

        return variables

    def is_initialized(self) -> bool:
        """Check if dotman has been initialized."""
        return self.dotman_dir.exists() and self.config_path.exists()

    def init(self) -> None:
        """Initialize dotman configuration in the current repo directory."""
        self.dotman_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            default_global = {
                "settings": {
                    "backup_dir": ".dotman/backups",
                    "template_suffix": ".j2",
                },
                "variables": {},
                "packages": {},
            }
            with open(self.config_path, "w") as f:
                yaml.dump(default_global, f, default_flow_style=False, sort_keys=False)

        if not self.local_config_path.exists():
            default_local: dict[str, Any] = {
                "packages": [],
                "variables": {},
                "file_overrides": {},
            }
            with open(self.local_config_path, "w") as f:
                yaml.dump(default_local, f, default_flow_style=False, sort_keys=False)

        self._global_config = None
        self._local_config = None
