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
