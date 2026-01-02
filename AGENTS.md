# Agent Guidelines for Dotman

This file provides guidelines for AI agents operating in the Dotman repository.

## Build, Lint, and Test Commands

### Installation

```bash
# Install the package in development mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"
```

### Linting and Formatting

```bash
# Run ruff linter (checks E, F, I, UP rules)
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Format code with ruff
ruff format .

# Run mypy type checker
mypy .
```

### Testing

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_config.py

# Run a specific test class
pytest tests/test_config.py::TestConfig

# Run a specific test method
pytest tests/test_config.py::TestConfig::test_load_global_config

# Run tests with verbose output
pytest -v

# Run tests with coverage
pytest --cov=dotman
```

### Code Coverage

```bash
# Run tests with coverage tracking
coverage run -m pytest tests/ -q

# View coverage report in terminal
coverage report

# View detailed coverage report by module
coverage report -m

# Generate HTML coverage report (opens in browser)
coverage html
# Open htmlcov/index.html in browser

# Generate XML coverage report (for CI/CD)
coverage xml

# Generate JSON coverage report (for tools)
coverage json

# Check coverage meets minimum threshold (fails if below 80%)
coverage report --fail-under=80

# Combine coverage from multiple runs
coverage combine

# Erase coverage data
coverage erase
```

**Coverage Configuration**:
- Configuration file: `.coveragerc`
- Reports generated:
  - Terminal: `coverage report`
  - HTML: `htmlcov/index.html`  
  - XML: `coverage.xml` (CI/CD compatible)
  - JSON: `coverage.json` (tool integration)

**Coverage Goals**:
- Core modules (config, link_manager, template_engine, exceptions): 95%+
- Overall project coverage: 80%+
- CLI integration tests: Improve from 0% to 70%

### Running the Application

```bash
# Run dotman CLI
dotman --help

# Initialize in a directory
dotman init

# Deploy dotfiles
dotman deploy

# Dry run deployment
dotman deploy --dry-run
```

## Code Style Guidelines

### Imports

- Use isort-style ordering: future → standard-library → third-party → first-party → local-folder
- Combine as-imports where appropriate
- Keep imports sorted alphabetically within sections
- Example:

  ```python
  from pathlib import Path
  from typing import Annotated

  import typer
  from rich.console import Console

  from dotman.config import Config
  from dotman.exceptions import DotmanError
  ```

### Formatting

- Use ruff formatter with default settings
- Double quotes for strings
- Space indentation (4 spaces)
- No trailing commas
- Keep line length reasonable (default ruff: 88 chars)

### Type Hints

- Use type hints for function signatures
- Prefer `pathlib.Path` over string paths
- Use `| None` syntax (Python 3.10+ union syntax)
- Annotated types for CLI arguments:
  ```python
  def deploy(
      packages: Annotated[
          list[str] | None,
          typer.Argument(help="Packages to deploy"),
      ] = None,
  ) -> None:
  ```

### Naming Conventions

- **Classes**: PascalCase (e.g., `LinkManager`, `Config`)
- **Functions/Variables**: snake_case (e.g., `get_link_status`, `backup_dir`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `TEMPLATE_PATTERN`)
- **Private Methods**: leading underscore (e.g., `_create_symlink`)
- **Module Names**: snake_case

### Error Handling

- Use custom exception hierarchy extending `DotmanError`
- Catch specific exceptions, not bare `Exception`
- Provide meaningful error messages
- Example:

  ```python
  class DotmanError(Exception):
      """Base exception for all Dotman errors."""
      pass

  class LinkExistsError(LinkError):
      """Target already exists and is not a symlink."""
      pass
  ```

### Code Structure

- Keep functions focused and small
- Use dataclasses for simple data structures
- Separate concerns into modules (config.py, link_manager.py, template_engine.py)
- Use Pydantic models for configuration schemas

### Docstrings

- Use Google-style docstrings
- Include Args and Returns sections for functions
- Example:

  ```python
  def get_link_status(self, source: Path, target: Path) -> LinkStatus:
      """Check the status of a symlink.

      Args:
          source: The source file path
          target: The target symlink path

      Returns:
          The current LinkStatus of the target
      """
  ```

### Pydantic Models

- Use for configuration and data validation
- Leverage Field for defaults and descriptions
- Example:
  ```python
  class PackageConfig(BaseModel):
      depends: list[str] = Field(default_factory=list)
      files: list[FileMapping] = Field(default_factory=list)
      variables: dict[str, Any] = Field(default_factory=dict)
  ```

### CLI with Typer

- Use Annotated arguments for help text
- Group related commands with Typer's app
- Provide helpful command descriptions
- Use Rich console for colored output

### Key Files

- `dotman/cli.py`: CLI commands using Typer
- `dotman/config.py`: Configuration loading (Pydantic)
- `dotman/link_manager.py`: Symlink operations
- `dotman/template_engine.py`: Jinja2 rendering
- `dotman/exceptions.py`: Exception hierarchy

### Module Organization

- Keep public API in `__init__.py` minimal
- Use relative imports within the package
- Avoid circular imports by careful ordering
