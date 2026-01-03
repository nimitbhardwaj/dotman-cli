# dotman

A modern, Pythonic dotfile manager that uses symbolic links and Jinja2 templates to manage your configuration files across multiple machines.

## Features

- **Simple Configuration** - YAML-based configuration with package organization
- **Symlink Management** - Create, remove, and track symlinks safely with backup support
- **Auto-Template Detection** - Files ending with `.j2` are automatically detected as templates
- **Template Change Detection** - Status command shows "Modified" or "Synced" for template files with whitespace normalization
- **File Absorption** - Automatically absorb new files from target directories into your dotfiles repository
- **Smart Template Handling** - Absorb skips template outputs to avoid duplicates
- **Strict Dependency Enforcement** - Dependencies must be defined in config.yaml and enabled in local.yaml with clear error messages
- **Machine-Specific Settings** - Override configurations per machine with local.yaml
- **Dry-Run Mode** - Preview changes before applying them
- **Rich Output** - Beautiful terminal output with status tables and color-coded feedback

## Quick Start

### Installation

```bash
# Official method - install with pipx
pipx install dotman

# From source
git clone https://github.com/nimitbhardwaj/dotman
cd dotman
pipx install .
```

### Basic Usage

```bash
# Initialize in your dotfiles repository
cd ~/.dotfiles
dotman init

# Edit .dotman/config.yaml with your configurations
dotman deploy --dry-run  # Preview changes
dotman deploy --force    # Apply changes

# Check status of deployed dotfiles
dotman status

# List all configured packages
dotman list

# Absorb new files from target directories
dotman absorb           # Absorb all unmanaged files
dotman absorb nvim      # Absorb only for nvim package
```

## Configuration

### Global Configuration (`.dotman/config.yaml`)

Define packages and file mappings:

```yaml
settings:
  backup_dir: ".dotman/backups"

variables:
  editor: "nvim"
  theme: "dracula"

packages:
  bash:
    files:
      - source: "bash/bashrc"
        target: "~/.bashrc"
      - source: "bash/bash_profile"
        target: "~/.bash_profile"

  nvim:
    depends: []
    files:
      - source: "nvim"
        target: "~/.config/nvim"
    variables:
      theme: "dracula"
```

### Local Configuration (`.dotman/local.yaml`)

Machine-specific overrides:

```yaml
packages:
  - bash
  - nvim

variables:
  theme: "onedark"

file_overrides:
  bash_profile:
    target: "~/.bashrc"
```

### File Mapping Options

```yaml
packages:
  myconfig:
    files:
      # Simple symlink
      - source: "config.conf"
        target: "~/.config.conf"

      # Template file (rendered with variables, detected by .j2 extension)
      - source: "template.conf.j2"
        target: "~/.rendered.conf"

      # Directory (recursively symlinks all files)
      - source: "mydir"
        target: "~/.mydir"
```

## Commands

| Command                      | Description                            |
| ---------------------------- | -------------------------------------- |
| `dotman init`                | Initialize dotman in current directory |
| `dotman deploy [packages]`   | Deploy dotfiles (create symlinks)      |
| `dotman undeploy [packages]` | Remove deployed symlinks               |
| `dotman status [packages]`   | Show status of deployed dotfiles       |
| `dotman list`                | List all available packages            |
| `dotman absorb [packages]`   | Absorb unmanaged files from target directories |

### Options

- `--config-dir, -c` - Override the config directory (default: `.dotman/` in current directory or `DOTMAN_CONFIG_DIR` env var)
- `--dry-run, -n` - Preview changes without applying them
- `--force, -f` - Overwrite existing files (with backup)
- Specific packages can be passed to commands for targeted operations

## File Absorption

Dotman can absorb new files from your target directories into your dotfiles repository:

```bash
# Absorb all unmanaged files from configured targets
dotman absorb

# Absorb only for specific packages
dotman absorb nvim bash
```

### How Absorption Works

When you run `dotman absorb`, dotman:

1. Scans configured target directories for new/unmanaged files
2. Copies each new file to the corresponding source location in your dotfiles repository
3. Creates a symlink from the source to the target (replacing the original file)
4. Preserves the directory structure relative to the target

### Smart Skipping

Absorption automatically skips:
- **Symlinks** - Already managed files
- **Template outputs** - Files rendered from `.j2` templates (avoids duplicates)
- **Existing files** - Files already present in the package source
- **Ignored patterns** - Files matching `absorb_ignore` patterns

### Ignore Patterns

You can specify patterns to ignore during absorption using `absorb_ignore`:

```yaml
packages:
  nvim:
    files:
      - source: "nvim"
        target: "~/.config/nvim"
        absorb_ignore:
          - "node_modules"      # Ignore any path containing node_modules
          - "*.log"             # Ignore log files
          - ".git/**"           # Ignore git directories
```

The `absorb_ignore` field accepts a list of regex patterns that are matched against the full file path. If a file matches any pattern, it will be skipped during absorption.

### Overlapping Targets

If multiple packages target the same directory, the first package (alphabetically) processes the files, and subsequent packages are skipped with a warning. This ensures predictable behavior:

```yaml
packages:
  nvim-base:
    files:
      - source: "nvim/base"
        target: "~/.config/nvim"
  
  nvim-home:
    files:
      - source: "nvim/home"
        target: "~/.config/nvim"  # Will be skipped, nvim-base processes first
```

### Dry Run Mode

Use `--dry-run` to preview what would be absorbed without making changes:

```bash
dotman absorb --dry-run
```

When a new file appears in a target directory (e.g., `~/.config/nvim/new_setting.json`), dotman will:
1. Move the file to the corresponding source directory in your dotfiles repository
2. Replace the original file with a symlink pointing to the source

### Absorb Ignore Patterns

You can specify patterns to ignore during absorption using regex:

```yaml
packages:
  nvim:
    files:
      - source: "nvim"
        target: "~/.config/nvim"
        absorb_ignore:
          - "node_modules"      # Ignore any path containing node_modules
          - "\\.git"            # Ignore any path containing .git
          - ".*\\.log"          # Ignore any .log files
```

### Smart Template Handling

When absorbing files, dotman automatically skips files that are template outputs. If a `.j2` template exists in your source (e.g., `config.conf.j2`), the rendered file in the target (e.g., `config.conf`) will not be absorbed to avoid duplicates.

## Architecture

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
│       └── exceptions.py       # Custom exceptions
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_link_manager.py
│   ├── test_template_engine.py
│   └── test_exceptions.py
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── AGENTS.md                   # Guidelines for AI agents
└── TODO.md                     # Development roadmap
```
dotman-cli/
├── src/
│   └── dotman/              # Python package
│       ├── __init__.py
│       ├── main.py             # Entry point
│       ├── cli.py              # Typer CLI commands
│       ├── config.py           # Configuration loading and validation
│       ├── link_manager.py     # Symlink creation and management
│       ├── template_engine.py  # Jinja2 template rendering
│       └── exceptions.py       # Custom exceptions
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_link_manager.py
│   ├── test_template_engine.py
│   └── test_exceptions.py
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── AGENTS.md                   # Guidelines for AI agents
└── TODO.md                     # Development roadmap

## Safety Features

- **Automatic Backups** - Existing files are backed up before overwriting
- **Dry-Run Mode** - Preview all operations before execution
- **Status Checking** - Detects broken, missing, and conflicting symlinks
- **Confirmation Prompts** - Destructive operations can require confirmation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
