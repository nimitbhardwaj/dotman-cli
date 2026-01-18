# Dotman - Pythonic Dotfile Manager

A Python-based dotfile manager that replicates Dotter's functionality with a Pythonic approach, making it easy to use for end users.

## Features

### ✅ Phase 1: Core Functionality (COMPLETED)

- [x] **Configuration System**
  - [x] YAML-based configuration (config.yaml and local.yaml)
  - [x] Package-based organization
  - [x] File mapping with target paths
  - [x] Basic variable support

- [x] **Symlink Management**
  - [x] Create symbolic links from repository to home directory
  - [x] Remove symlinks (with backup option)
  - [x] Detect and handle broken symlinks
  - [x] Force relink functionality
  - [x] Dry-run mode for previewing changes

- [x] **Template System**
  - [x] Jinja2 templating integration
  - [x] Variable substitution {{variable_name}}
  - [x] Auto-detect templates by `.j2` extension (preferred method)
  - [x] Template change detection with Modified/Synced status
  - [x] Removed manual template override (auto-detection is sufficient)

- [x] **CLI Commands**
  - [x] `dotman init` - Initialize dotman in current directory
  - [x] `dotman deploy` - Deploy dotfiles (with --dry-run and --force flags)
  - [x] `dotman undeploy` - Remove deployed symlinks
  - [x] `dotman status` - Show managed files and their status
  - [x] `dotman list` - List all available packages

### ✅ Phase 2: Advanced Configuration (COMPLETED)

- [x] **Package Dependencies**
  - [x] Package dependency system with strict enforcement
  - [x] Dependency validation (must be defined in config.yaml)
  - [x] Dependency enablement (must be enabled in local.yaml)
  - [x] Clear error messages for missing dependencies
  - [x] Circular dependency detection

- [x] **Machine-Specific Configuration**
  - [x] local.yaml support for machine-specific settings
  - [x] Configuration merging (config.yaml + local.yaml)
  - [x] Variable overrides per machine

### ✅ Phase 3: Pythonic Enhancements (COMPLETED)

- [x] **Python-Specific Improvements**
  - [x] Use pathlib for all path operations
  - [x] Type hints throughout the codebase
  - [x] Rich library for beautiful CLI output
  - [x] Typer for CLI (Pythonic approach)
  - [x] Pydantic for configuration validation

### ✅ Phase 4: Quality of Life (COMPLETED)

- [x] **User Experience**
  - [x] Colorful, informative output using Rich
  - [x] Clear error messages with suggestions

- [x] **Safety Features**
  - [x] Automatic backup before overwriting files
  - [x] Dry-run mode for previewing changes
  - [x] Validation of configuration before deployment
  - [x] pipx installation support (ONLY supported method)

- [x] **Environment Variable Support**
  - [x] DOTMAN_CONFIG_DIR environment variable for config directory
  - [x] `--config-dir` / `-c` CLI flag to override config directory
  - [x] Priority: CLI flag > env var > auto-detect (.dotman/)

### ✅ Phase 4.5: File Absorption (COMPLETED)

- [x] **dotman absorb Command**
  - [x] Absorb unmanaged files from target directories
  - [x] Dry-run mode (--dry-run flag)
  - [x] Package-specific absorption (positional arguments)
  - [x] Verbose output for debugging

- [x] **Exclude Patterns**
  - [x] absorb_ignore patterns in config.yaml per file mapping
  - [x] Support for regex patterns
  - [x] Configuration in config.yaml:
    ```yaml
    packages:
      myconfig:
        files:
          - source: "config"
            target: "~/.config"
            absorb_ignore:
              - "node_modules/**"
              - ".git/**"
    ```

- [x] **File Discovery**
  - [x] Scan target directories for unmanaged files
  - [x] Detect if file is already a symlink (skip)
  - [x] Detect if file is template-generated (skip)
  - [x] Match destination path to package
  - [x] Handle multiple packages with same destination (first alphabetically wins)

- [x] **File Absorption Logic**
  - [x] Move file to package source directory
  - [x] Preserve directory structure
  - [x] Create symlink after absorption

### ✅ Phase 4.6: Deployment History & Rollback (COMPLETED)

- [x] **Deployment History**
  - [x] Track all deployments in `.dotman/history.yaml`
  - [x] Unique deployment IDs (UUID prefix)
  - [x] `dotman history` command with --limit option
  - [x] Records packages, files, and deployment type (live/dry-run)

- [x] **Rollback Support**
  - [x] `dotman rollback` command (latest or by ID)
  - [x] Remove symlinks created during deployment
  - [x] Restore original files from backups
  - [x] Remove rendered template files
  - [x] Remove deployment from history
  - [x] Dry-run mode for previewing rollback
  - [x] Summary of processed/skipped/failed files

### ✅ Phase 5: Hooks System (COMPLETED)

- [x] **Hook Configuration**
  - [x] HookConfig model in config.py
  - [x] Pre/post deploy hook support
  - [x] Configuration in config.yaml per package

- [x] **Hook Execution**
  - [x] HookExecutor class in hook_executor.py
  - [x] Execute pre_deploy hooks before file deployment
  - [x] Execute post_deploy hooks after file deployment
  - [x] Abort deployment on pre_deploy hook failure
  - [x] Continue deployment on post_deploy hook failure (log error)
  - [x] Dry-run mode skips hook execution
  - [x] Display hook execution in console output

- [x] **Template Variables in Hooks**
  - [x] {{package_name}} - Name of the current package
  - [x] {{dotfiles_dir}} - Path to your dotfiles repository
  - [x] {{target_dir}} - Path to the target directory for the package
  - [x] {{variable_name}} - Any variables defined in your configuration
  - [x] Jinja2 template rendering in hooks
  - [x] Jinja2 filters and conditionals

- [x] **Error Handling**
  - [x] HookExecutionError with exit code and output
  - [x] Clear error messages

- [x] **Testing**
  - [x] Unit tests (24 tests passing)
  - [x] Integration with deploy command

### Phase 6: Advanced Features (FUTURE)

- [ ] **Package Include System**
  - [ ] Include additional YAML files
  - [ ] Package dependencies with composition
  - [ ] Configuration merging with precedence
  - [ ] OS-specific configuration includes
  - [ ] Dependency resolution (topological sort)
  - [ ] Circular dependency detection

- [ ] **Watch Mode**
  - [ ] `dotman watch` - continuously monitor and deploy changes
  - [ ] Debounced deployment to avoid rapid successive runs
  - [ ] File system watchers (inotify on Linux, kqueue on macOS)

### Phase 7: Remote & Sync Features (FUTURE)

- [ ] **Remote Repository Support**
  - [ ] Clone dotfiles from remote repository
  - [ ] Push/pull from GitHub/GitLab
  - [ ] Multiple repository support

- [ ] **Template Caching**
  - [ ] Cache compiled templates for performance
  - [ ] Cache state detection to avoid redundant operations
  - [ ] Automatic cache invalidation

### Phase 8: Polish & Documentation (COMPLETED)

- [x] **Documentation**
  - [x] Comprehensive README.md
  - [x] Command help text
  - [x] AGENTS.md for AI coding agents

- [x] **Testing**
  - [x] Unit tests for core functionality
  - [x] Test coverage tracking
  - [x] Integration tests for CLI commands
  - [x] 177+ tests passing

## Architecture

### Current Directory Structure

```
dotman/
├── src/
│   └── dotman/              # Python package
│       ├── __init__.py
│       ├── main.py             # Entry point
│       ├── cli.py              # Typer CLI commands
│       ├── config.py           # Configuration loading and validation
│       ├── link_manager.py     # Symlink creation and management
│       ├── template_engine.py  # Jinja2 template rendering
│       ├── hook_executor.py    # Hook execution for shell commands
│       ├── history.py          # Deployment history tracking
│       └── exceptions.py       # Custom exceptions
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_link_manager.py
│   ├── test_template_engine.py
│       ├── test_exceptions.py
│       ├── test_hooks.py       # 24 tests for hooks
│       ├── test_cli_deploy.py
│       ├── test_cli_status.py
│       └── ...
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── AGENTS.md                   # Guidelines for AI agents
└── TODO.md                     # Development roadmap
```

## Installation

### From Source

```bash
git clone https://github.com/nimitbhardwaj/dotman
cd dotman
pip install -e .
```

### From PyPI (when published)

```bash
pip install dotman
```

## Usage

### Quick Start

```bash
# Initialize in your dotfiles repository
cd ~/.dotfiles
dotman init

# Edit .dotman/config.yaml with your configurations
dotman deploy --dry-run  # Preview changes
dotman deploy --force    # Apply changes

# Check status (shows Modified/Synced for templates)
dotman status

# List all packages with dependencies
dotman list
```

### Hooks Usage

Hooks execute shell commands before and after package deployment:

```yaml
packages:
  nvim:
    files:
      - source: "nvim"
        target: "~/.config/nvim"
    hooks:
      pre_deploy:
        - "echo 'Starting deployment'"
        - "mkdir -p ~/.config/nvim"
      post_deploy:
        - "nvim --headless -c 'PlugInstall --sync' -c 'qall'"
```

Available template variables in hooks:
- `{{package_name}}` - Name of the current package
- `{{dotfiles_dir}}` - Path to your dotfiles repository
- `{{target_dir}}` - Path to the target directory for the package
- `{{variable_name}}` - Any variables defined in your configuration

Example with configuration variables:

```yaml
packages:
  nvim:
    variables:
      theme: "dracula"
    hooks:
      pre_deploy:
        - "echo 'Installing {{theme}} theme'"
      post_deploy:
        - "echo 'Theme {{theme}} installed!'"
```

Conditional execution:

```yaml
packages:
  nvim:
    variables:
      debug: true
    hooks:
      pre_deploy:
        - "{% if debug %}echo 'Debug mode enabled'{% endif %}"
```

### Dependency Management

```yaml
# config.yaml
packages:
  nvim-base:
    files:
      - source: "nvim/base"
        target: "~/.config/nvim"

  nvim-home:
    depends: ["nvim-base"]  # Depends on nvim-base
    files:
      - source: "nvim/home"
        target: "~/.config/nvim"

# local.yaml
packages:
  - nvim-base
  - nvim-home  # nvim-base will be auto-included
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
