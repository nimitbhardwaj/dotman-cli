"""Executable checking services for the doctor command."""

import shutil
from typing import Literal

from pydantic import BaseModel, Field


class DoctorCheckResult(BaseModel):
    """Result of a single executable check for a package."""

    package_name: str
    executable_name: str
    found: bool
    path: str | None
    severity: Literal["error", "warning"]


class DoctorCommandResult(BaseModel):
    """Result of the doctor command for a single package."""

    package_name: str
    checks: list[DoctorCheckResult] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)

    def compute_summary(self) -> dict[str, int]:
        """Compute summary statistics from checks.

        Returns:
            A dictionary with totals for 'errors', 'warnings', and 'passed'.
        """
        errors = 0
        warnings = 0
        passed = 0

        for check in self.checks:
            if check.found:
                passed += 1
            elif check.severity == "error":
                errors += 1
            else:
                warnings += 1

        return {"errors": errors, "warnings": warnings, "passed": passed}


class ExecutableChecker:
    """Checks if executables are present in the system PATH."""

    def __init__(self) -> None:
        """Initialize the executable checker with an empty cache."""
        self._cache: dict[str, tuple[bool, str | None]] = {}

    def find_executable(self, name: str) -> tuple[bool, str | None]:
        """Find an executable in the system PATH.

        Args:
            name: The name of the executable to find.

        Returns:
            A tuple of (found, path) where:
            - found: True if the executable exists in PATH
            - path: The full path to the executable if found, None otherwise
        """
        if not name:
            return (False, None)

        name = name.strip()

        if not name:
            return (False, None)

        if name in self._cache:
            return self._cache[name]

        try:
            path: str | None = shutil.which(name)
            if path is not None:
                result: tuple[bool, str | None] = (True, path)
            else:
                result = (False, None)
        except (OSError, TypeError, ValueError):
            result = (False, None)

        self._cache[name] = result
        return result

    def find_executables(self, names: list[str]) -> dict[str, tuple[bool, str | None]]:
        """Find multiple executables in the system PATH.

        Args:
            names: List of executable names to find.

        Returns:
            A dictionary mapping executable names to (found, path) tuples.
        """
        return {name: self.find_executable(name) for name in names}

    def clear_cache(self) -> None:
        """Clear the executable cache."""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached lookups.

        Returns:
            The number of executables in the cache.
        """
        return len(self._cache)
