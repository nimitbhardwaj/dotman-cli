# PRD: Dotman Phase 2 - Core Module Organization and Test Structure Alignment

## Overview

Phase 1 refactoring organized CLI commands into `src/dotman/cli/commands/` with partial test mirroring. Phase 2 extends this organization to the remaining modules in `src/dotman/`, grouping them into logical directories (core/, managers/, services/) and fully mirroring the new structure in tests/.

## Goals

- Group related modules into logical directories (core/, managers/, services/)
- Create cleaner separation between CLI and core functionality
- Rename `commands.py` to `cli_utils.py`
- Mirror the new src structure in tests/ directory
- Ensure all imports and references are updated consistently

## Quality Gates

These commands must pass for every user story:
- `uv run ruff check .` - Linting
- `uv run ruff format --check .` - Formatting check
- `uv run mypy .` - Type checking
- `uv run pytest` - All tests passing

## User Stories

### US-001: Create core/ directory with fundamental modules
Create `src/dotman/core/` directory. Move `config.py`, `link_manager.py`, `template_engine.py`, `exceptions.py` to core directory. Create `__init__.py` with exports. Update imports in affected modules.

### US-002: Create managers/ directory with operational modules
Create `src/dotman/managers/` directory. Move `remote.py`, `repository.py`, `history.py`, `watcher.py` to managers directory. Create `__init__.py` with exports.

### US-003: Create services/ directory with execution services
Create `src/dotman/services/` directory. Move `hook_executor.py` to services directory. Create `__init__.py` with exports.

### US-004: Rename commands.py to cli_utils.py
Rename `src/dotman/commands.py` to `src/dotman/cli_utils.py`. Update all import statements that reference `commands.py`.

### US-005: Update CLI module imports for new structure
Update `src/dotman/cli/__init__.py` and `src/dotman/cli/commands/*.py` imports for new core/managers/services structure.

### US-006: Create tests/core/ directory mirroring core modules
Create `tests/core/` directory. Move `test_config.py`, `test_link_manager.py`, `test_template_engine.py`, `test_exceptions.py` to tests/core.

### US-007: Create tests/managers/ directory mirroring managers modules
Create `tests/managers/` directory. Move `test_remote.py`, `test_watcher.py` to tests/managers.

### US-008: Create tests/services/ directory mirroring services modules
Create `tests/services/` directory. Move `test_hooks.py` to tests/services.

### US-009: Update root-level test files for new structure
Handle `test_template_rendering_in_directories.py` and `conftest.py`. Determine appropriate locations and update imports.

### US-010: Update AGENTS.md with new project structure
Update AGENTS.md documentation with new core/managers/services directory structure.

### US-011: Run full quality gate verification
Run all quality commands and verify everything passes.

## Target Structure

```
src/dotman/
├── cli/
├── core/
├── managers/
├── services/
├── cli_utils.py  # renamed from commands.py
└── ...
```
