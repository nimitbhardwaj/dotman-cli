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
  - [x] PyYAML for YAML parsing
  - [x] Pydantic for configuration validation

### Phase 4: Quality of Life (IN PROGRESS)

- [x] **User Experience**
  - [x] Colorful, informative output using Rich
  - [x] Clear error messages with suggestions

- [x] **Safety Features**
  - [x] Automatic backup before overwriting files
  - [x] Dry-run mode for previewing changes
  - [x] Validation of configuration before deployment

- [ ] **Progress Indicators**
  - [ ] Progress indicators for large deployments
  - [ ] Interactive prompts for missing configuration
  - [ ] Verbose mode for detailed logging

### Phase 5: Advanced Features (FUTURE)

- [ ] **Watch Mode**
  - [ ] `dotman watch` - continuously monitor and deploy changes
  - [ ] Debounced deployment to avoid rapid successive runs
  - [ ] File system watchers (inotify on Linux, kqueue on macOS)

- [ ] **Hooks System**
  - [ ] Pre/post deploy hooks
  - [ ] Pre/post undeploy hooks
  - [ ] Hooks rendered as templates
  - [ ] Hook execution with error handling

- [ ] **Include System**
  - [ ] Include additional YAML files
  - [ ] Configuration merging with precedence
  - [ ] OS-specific configuration includes

### Phase 6: Remote & Sync Features (FUTURE)

- [ ] **Remote Repository Support**
  - [ ] Clone dotfiles from remote repository
  - [ ] Push/pull from GitHub/GitLab
  - [ ] Multiple repository support

- [ ] **Template Caching**
  - [ ] Cache compiled templates for performance
  - [ ] Cache state detection to avoid redundant operations
  - [ ] Automatic cache invalidation

### Phase 7: Polish & Documentation (COMPLETED)

- [x] **Documentation**
  - [x] Comprehensive README.md
  - [x] Command help text
  - [x] AGENTS.md for AI coding agents

- [x] **Testing**
  - [x] Unit tests for core functionality (177 tests)
  - [x] Test coverage tracking
  - [x] Integration tests for CLI commands

- [ ] **Packaging**
  - [ ] PyPI package setup
  - [ ] Wheel distribution
  - [ ] Homebrew formula (for macOS)
  - [ ] pipx installation support

## Architecture

### Directory Structure

```
dotman/
├── dotman/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── cli.py               # Typer commands
│   ├── config.py            # Configuration loading and validation
│   ├── link_manager.py      # Symlink creation and management
│   ├── template_engine.py   # Jinja2 template rendering
│   └── exceptions.py        # Custom exceptions
├── tests/
│   ├── __init__.py
│   ├── test_config.py       # 51 tests
│   ├── test_link_manager.py # 44 tests
│   ├── test_template_engine.py # 41 tests
│   └── test_exceptions.py   # 41 tests
├── .dotman/
│   ├── config.yaml          # Global configuration
│   ├── local.yaml           # Machine-specific configuration
│   └── backups/             # Backup directory
└── pyproject.toml
```

**Configuration File Format**

**config.yaml (Example):**

```yaml
settings:
  backup_dir: ".dotman/backups"

variables:
  editor: "nvim"
  theme: "dracula"

packages:
  nvim-base:
    files:
      - source: "nvim"
        target: "~/.config/nvim"

  nvim-home:
    depends: ["nvim-base"]
    files:
      - source: "nvim/home/settings.yaml.j2"
        target: "~/.config/nvim/settings.yaml"
    variables:
      theme: "dracula"
```

**local.yaml (Example):**

```yaml
packages:
  - nvim-base
  - nvim-home

variables:
  theme: "onedark"
```

## Installation

### From Source

```bash
git clone https://github.com/yourusername/dotman
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

### Template Usage

Templates are automatically detected by `.j2` extension:

```bash
# File: nvim/settings.yaml.j2
editor = {{editor}}
theme = {{theme}}

# Configuration:
packages:
  nvim:
    files:
      - source: "nvim/settings.yaml.j2"  # Auto-detected as template
        target: "~/.config/nvim/settings.yaml"
    variables:
      theme: "dracula"
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
4. Ensure all tests pass (177 tests)
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
