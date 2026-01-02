# dotman-cli

A modern, Pythonic dotfile manager that uses symbolic links and Jinja2 templates to manage your configuration files across multiple machines.

## Features

- **Simple Configuration** - YAML-based configuration with package organization
- **Symlink Management** - Create, remove, and track symlinks safely with backup support
- **Auto-Template Detection** - Files ending with `.j2` are automatically detected as templates
- **Template Change Detection** - Status command shows "Modified" or "Synced" for template files with whitespace normalization
- **Strict Dependency Enforcement** - Dependencies must be defined in config.yaml and enabled in local.yaml with clear error messages
- **Machine-Specific Settings** - Override configurations per machine with local.yaml
- **Dry-Run Mode** - Preview changes before applying them
- **Rich Output** - Beautiful terminal output with status tables and color-coded feedback

## Quick Start

### Installation

```bash
# Official method - install with pipx
pipx install dotman-cli

# From source
git clone https://github.com/yourusername/dotman-cli
cd dotman-cli
pipx install .
```

### Basic Usage

```bash
# Initialize in your dotfiles repository
cd ~/.dotfiles
dotman-cli init

# Edit .dotman/config.yaml with your configurations
dotman-cli deploy --dry-run  # Preview changes
dotman-cli deploy --force    # Apply changes

# Check status of deployed dotfiles
dotman-cli status

# List all configured packages
dotman-cli list
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
| `dotman-cli init`            | Initialize dotman-cli in current directory |
| `dotman-cli deploy [packages]`   | Deploy dotfiles (create symlinks)      |
| `dotman-cli undeploy [packages]` | Remove deployed symlinks               |
| `dotman-cli status [packages]`   | Show status of deployed dotfiles       |
| `dotman-cli list`            | List all available packages            |

### Options

- `--dry-run, -n` - Preview changes without applying them
- `--force, -f` - Overwrite existing files (with backup)
- Specific packages can be passed to commands for targeted operations

## Templates

Dotman supports Jinja2 templates for files that need variable substitution:

```jinja2
# Example template.conf
{{_comment_}} This is a comment
editor = {{editor}}
theme = {{theme}}
```

Template variables can be defined at:

- Global level (`.dotman/config.yaml`)
- Package level (within package definition)
- Local level (`.dotman/local.yaml`)

Variables are merged with precedence: package > local > global

## Architecture

```
dotman-cli/
├── dotman/              # Python package (remains "dotman")
│   ├── cli.py              # Typer CLI commands
│   ├── config.py           # Configuration loading and validation
│   ├── link_manager.py     # Symlink creation and management
│   ├── template_engine.py  # Jinja2 template rendering
│   ├── exceptions.py       # Custom exceptions
│   └── main.py             # Entry point
├── .dotman/
│   ├── config.yaml         # Global configuration
│   ├── local.yaml          # Machine-specific configuration
│   └── backups/            # Backup directory
└── tests/
    └── __init__.py
```

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
