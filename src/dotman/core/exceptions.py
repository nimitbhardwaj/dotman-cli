"""Custom exceptions for Dotman."""


class DotmanError(Exception):
    """Base exception for all Dotman errors."""

    pass


class ConfigError(DotmanError):
    """Configuration-related errors."""

    pass


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""

    pass


class ConfigParseError(ConfigError):
    """Error parsing configuration file."""

    pass


class ConfigIncludeError(ConfigError):
    """Error including configuration file."""

    pass


class ConfigIncludeNotFoundError(ConfigIncludeError):
    """Included configuration file not found."""

    pass


class CircularIncludeError(ConfigIncludeError):
    """Circular reference detected in configuration includes."""

    pass


class LinkError(DotmanError):
    """Symlink-related errors."""

    pass


class LinkExistsError(LinkError):
    """Target already exists and is not a symlink."""

    pass


class LinkTargetMissingError(LinkError):
    """Source file for symlink does not exist."""

    pass


class TemplateError(DotmanError):
    """Template-related errors."""

    pass


class TemplateRenderError(TemplateError):
    """Error rendering a template."""

    pass


class PackageError(DotmanError):
    """Package-related errors."""

    pass


class PackageNotFoundError(PackageError):
    """Package not found in configuration."""

    pass


class DependencyError(PackageError):
    """Dependency resolution error."""

    pass


class MissingDependencyError(DependencyError):
    """Required dependency package is not defined in configuration."""

    pass


class CircularDependencyError(DependencyError):
    """Circular dependency detected between packages."""

    pass


class HookError(DotmanError):
    """Hook-related errors."""

    pass


class HookExecutionError(HookError):
    """Error executing a hook."""

    pass


class HistoryError(DotmanError):
    """History-related errors."""

    pass


class RollbackError(DotmanError):
    """Rollback-related errors."""

    pass


class RemoteError(DotmanError):
    """Remote repository-related errors."""

    pass


class RemoteCloneError(RemoteError):
    """Error cloning a remote repository."""

    pass


class RemoteFetchError(RemoteError):
    """Error fetching from a remote repository."""

    pass


class RemoteNotFoundError(RemoteError):
    """Remote repository not found."""

    pass


class RemoteAuthenticationError(RemoteError):
    """Authentication error for remote repository."""

    pass


class RemotePushError(RemoteError):
    """Error pushing to remote repository."""

    pass


class WatcherError(DotmanError):
    """File system watcher-related errors."""

    pass


class WatcherBackendError(WatcherError):
    """Error with file system watcher backend."""

    pass


class WatcherInitializationError(WatcherError):
    """Error initializing file system watcher."""

    pass


class RepositoryError(DotmanError):
    """Repository-related errors."""

    pass


class RepositoryNotFoundError(RepositoryError):
    """Repository not found in registry."""

    pass


class RepositoryAlreadyExistsError(RepositoryError):
    """Repository already exists in registry."""

    pass


class RepositoryPathError(RepositoryError):
    """Invalid repository path."""

    pass


class NothingToCommitError(RepositoryError):
    """No changes to commit in the repository."""

    pass


class DoctorError(DotmanError):
    """Doctor-related errors."""

    pass


class MissingExecutableError(DoctorError):
    """Required executable is not found in PATH."""

    pass
