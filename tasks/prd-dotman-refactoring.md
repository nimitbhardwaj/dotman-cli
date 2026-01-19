# PRD: Dotman Code Refactoring and Documentation Update

## Overview

Refactor the dotman codebase to improve code readability, maintainability, and organization. The codebase has grown to 1500+ lines in cli.py with scattered functionality, outdated AGENTS.md documentation, and a test structure that doesn't mirror the source code. This refactoring will restructure files for better separation of concerns, add minor improvements while preserving existing functionality, and update all documentation to reflect the current state and use uv for package management.

## Goals

- Reduce cli.py from 1500+ lines to manageable, focused command modules
- Mirror source code folder structure in tests/ directory
- Update AGENTS.md with accurate, uv-based commands and current project structure
- Improve code readability through better separation of concerns
- Add minor improvements that enhance maintainability without changing behavior
- Ensure all quality gates pass after refactoring

## Quality Gates

These commands must pass for every user story:

- `uv run ruff check .` - Linting (E, F, I, UP rules)
- `uv run ruff format --check .` - Formatting check
- `uv run mypy .` - Type checking
- `uv run pytest` - All tests passing
- `uv run pytest --cov=dotman` - Coverage report generation

## User Stories

### US-001: Refactor CLI init and clone commands into separate module
**Description:** As a developer, I want the init and clone commands extracted from cli.py into their own module so that the CLI file is more manageable.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/` directory
- [ ] Extract `init()` and `clone()` functions to `src/dotman/cli/commands/init.py`
- [ ] Extract `clone()` to `src/dotman/cli/commands/clone.py`
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for init and clone continue to pass
- [ ] Update test files to match new structure

### US-002: Refactor CLI push and pull commands into separate module
**Description:** As a developer, I want the push and pull commands extracted from cli.py into their own module so that git-related commands are grouped together.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/push.py` with `push()` function
- [ ] Create `src/dotman/cli/commands/pull.py` with `pull()` function
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for push and pull continue to pass
- [ ] Update test files to match new structure

### US-003: Refactor CLI deploy and undeploy commands into separate module
**Description:** As a developer, I want the deploy and undeploy commands extracted from cli.py into their own module so that deployment-related logic is grouped together.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/deploy.py` with `deploy()` and `undeploy()` functions
- [ ] Extract helper functions specific to deploy/undeploy (e.g., `_should_skip_file`, `_absorb_file`, `_absorb_directory`)
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for deploy and undeploy continue to pass
- [ ] Update test files to match new structure

### US-004: Refactor CLI status and list commands into separate module
**Description:** As a developer, I want the status and list commands extracted from cli.py into their own module for better organization.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/status.py` with `status()` and `list_packages()` functions
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for status and list continue to pass
- [ ] Update test files to match new structure

### US-005: Refactor CLI watch and history commands into separate module
**Description:** As a developer, I want the watch and history commands extracted from cli.py into their own module.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/watch.py` with `watch()` function
- [ ] Create `src/dotman/cli/commands/history.py` with `history()` and `rollback()` functions
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for watch and history continue to pass
- [ ] Update test files to match new structure

### US-006: Refactor CLI absorb command into separate module
**Description:** As a developer, I want the absorb command extracted from cli.py into its own module.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/absorb.py` with `absorb_changes()` function and helpers
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for absorb continue to pass
- [ ] Update test files to match new structure

### US-007: Refactor CLI repo subcommands into separate module
**Description:** As a developer, I want the repo subcommands extracted from cli.py into their own module.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/commands/repo.py` with all repo subcommand functions
- [ ] Update `src/dotman/cli.py` to import and use these functions
- [ ] All existing tests for repo commands continue to pass
- [ ] Update test files to match new structure

### US-008: Create CLI base module and utilities
**Description:** As a developer, I want a base CLI module with shared utilities so that command modules can reuse common functionality.

**Acceptance Criteria:**
- [ ] Create `src/dotman/cli/__init__.py` with shared utilities
- [ ] Move `get_config()` and `get_repository_option()` functions to base module
- [ ] Create shared console instance in base module
- [ ] Update all command modules to import from base module

### US-009: Restructure tests to mirror source code
**Description:** As a developer, I want tests organized in the same structure as source code so that it's easier to find corresponding tests.

**Acceptance Criteria:**
- [ ] Create `tests/cli/` directory mirroring `src/dotman/cli/` structure
- [ ] Move CLI tests to `tests/cli/commands/` subdirectory
- [ ] Create `tests/cli/__init__.py` if needed
- [ ] All tests continue to pass with new structure
- [ ] Update pytest configuration if needed

### US-010: Update AGENTS.md with uv-based commands
**Description:** As a developer, I want AGENTS.md updated to use uv commands so that documentation is accurate and current.

**Acceptance Criteria:**
- [ ] Replace `pip install -e .` with `uv sync` and `uv run`
- [ ] Update linting commands: `uv run ruff check .`
- [ ] Update formatting commands: `uv run ruff format .`
- [ ] Update type checking commands: `uv run mypy .`
- [ ] Update testing commands: `uv run pytest`
- [ ] Update coverage commands: `uv run coverage run -m pytest` and `uv run coverage report`
- [ ] Update all command examples to use uv prefix

### US-011: Update AGENTS.md with new project structure
**Description:** As a developer, I want AGENTS.md updated with the new CLI folder structure so that documentation matches the codebase.

**Acceptance Criteria:**
- [ ] Update "Key Files" section with new structure
- [ ] Add documentation for `cli/commands/` directory
- [ ] Add documentation for `cli/__init__.py`
- [ ] Update code style guidelines if needed

### US-012: Run full quality gate verification
**Description:** As a developer, I want to verify all quality gates pass after refactoring so that the codebase maintains its standards.

**Acceptance Criteria:**
- [ ] Run `uv run ruff check .` with no errors
- [ ] Run `uv run ruff format --check .` with no failures
- [ ] Run `uv run mypy .` with no errors
- [ ] Run `uv run pytest` with 100% pass rate
- [ ] Generate coverage report with `uv run coverage html`

## Functional Requirements

- FR-1: No functionality changes - all commands must work identically after refactoring
- FR-2: All existing tests must pass after restructuring
- FR-3: CLI module must maintain same public API
- FR-4: Import paths must be updated consistently across the codebase
- FR-5: Documentation must match current implementation
- FR-6: Test structure must mirror source structure

## Non-Goals

- No new CLI commands or features
- No changes to configuration file format
- No database schema changes
- No API changes to internal modules (config.py, link_manager.py, etc.)
- No changes to pyproject.toml tool configuration
- No performance optimizations (pure refactoring focus)

## Technical Considerations

### Current Structure Issues
- `cli.py` has grown to 1500+ lines with 18+ command functions
- Tests are flat in `tests/` without source mirroring
- AGENTS.md still references pip instead of uv
- Import chains are becoming complex

### Target Structure
```
src/dotman/
├── cli/
│   ├── __init__.py          # Base utilities, console, config helper
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py          # init command
│   │   ├── clone.py         # clone command
│   │   ├── deploy.py        # deploy, undeploy commands
│   │   ├── status.py        # status, list commands
│   │   ├── absorb.py        # absorb command
│   │   ├── watch.py         # watch command
│   │   ├── history.py       # history, rollback commands
│   │   ├── push.py          # push command
│   │   ├── pull.py          # pull command
│   │   └── repo.py          # repo subcommands
│   └── cli.py               # Main app, repo_app, Typer instances
```

```
tests/
├── cli/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── test_init.py
│       ├── test_clone.py
│       ├── test_deploy.py
│       ├── test_status.py
│       └── ...
```

### Import Strategy
- Use relative imports within CLI module
- Export command functions from `__init__.py` as needed
- Maintain backward compatibility for any external imports

## Success Metrics

- cli.py reduced to under 500 lines
- Tests mirror source structure 1:1
- All quality commands pass without errors
- Documentation accurately reflects codebase
- No functionality regressions
