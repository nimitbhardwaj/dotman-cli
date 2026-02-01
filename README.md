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
- **Circular Dependency Detection** - Detects and prevents circular dependencies between packages with clear error messages
- **Machine-Specific Settings** - Override configurations per machine with local.yaml
- **Dry-Run Mode** - Preview changes before applying them
- **Rich Output** - Beautiful terminal output with status tables and color-coded feedback
- **Hooks System** - Execute shell commands before and after deployments with template support
- **Deployment History** - Track all deployments with unique IDs for auditing
- **Rollback Support** - Restore previous deployments from history
- **Watch Mode** - Automatically deploy changes when files are modified
- **Remote Repository Support** - Clone, push, and pull from GitHub/GitLab
- **Template Caching** - Cache compiled templates for faster deployments
- **Package Include System** - Include and compose configuration files

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

| Command                      | Description                                    |
| ---------------------------- | ---------------------------------------------- |
| `dotman init`                | Initialize dotman in current directory         |
| `dotman deploy [packages]`   | Deploy dotfiles (create symlinks)              |
| `dotman undeploy [packages]` | Remove deployed symlinks                       |
| `dotman status [packages]`   | Show status of deployed dotfiles               |
| `dotman list`                | List all available packages                    |
| `dotman absorb [packages]`   | Absorb unmanaged files from target directories |
| `dotman watch`               | Watch for file changes and deploy automatically |
| `dotman clone <repo>`        | Clone a remote dotfiles repository             |
| `dotman push [remote]`       | Push changes to remote repository              |
| `dotman pull [remote]`       | Pull changes from remote repository            |
| `dotman history [--limit]`   | Show deployment history                        |
| `dotman rollback [id]`       | Rollback a deployment by ID                    |
| `dotman repo add <name>`     | Register current directory as a repository     |
| `dotman repo list`           | List all registered repositories               |
| `dotman doctor [packages]`   | Check required executables are present         |

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
          - "node_modules" # Ignore any path containing node_modules
          - "*.log" # Ignore log files
          - ".git/**" # Ignore git directories
```

The `absorb_ignore` field accepts a list of regex patterns that are matched against the full file path. If a file matches any pattern, it will be skipped during absorption.

## Doctor Configuration

Dotman can check if required executables are present on your system before deploying packages. This helps identify missing dependencies early, preventing partial deployments and confusing errors.

### Basic Configuration

Define executable requirements in your package configuration:

```yaml
packages:
  nvim:
    depends: []
    files:
      - source: "nvim"
        target: "~/.config/nvim"
    doctor:
      executables:
        - name: nvim
          severity: error
        - name: git
          severity: error
```

### Severity Levels

The `severity` field determines how missing executables are treated:

- **`error`**: The executable is required for the package to work. If missing, `dotman deploy` may fail or produce unexpected results. The doctor command returns exit code 1.
- **`warning`**: The executable is optional or only needed for certain features. If missing, the package may still work with reduced functionality. The doctor command returns exit code 0 but shows a warning.

### Example Configuration

```yaml
packages:
  nvim-base:
    description: "Neovim configuration with LazyVim for base"
    files:
      - source: "nvim/base/"
        target: "~/.config/nvim"
    doctor:
      executables:
        - name: nvim
          severity: error
        - name: git
          severity: error

  opencode:
    description: "OpenCode AI assistant configuration"
    files:
      - source: "opencode"
        target: "~/.config/opencode"
    doctor:
      executables:
        - name: node
          severity: warning
        - name: bun
          severity: warning

  zsh:
    description: "Zsh Config for the system"
    files:
      - source: "zsh/.zshrc"
        target: "~/.zshrc"
    doctor:
      executables:
        - name: zsh
          severity: error
```

### Using the Doctor Command

```bash
# Check all enabled packages
dotman doctor

# Check specific packages
dotman doctor nvim zsh

# Check with custom config directory
dotman doctor --config-dir ~/.dotfiles
```

### Example Output

```
$ dotman doctor

╭───────────────────────────────────────────────────────────────────────────╮
│ Doctor Check Results                                                      │
├───────────────────────────────────────────────────────────────────────────┤
│ Package: nvim-base                                                        │
├───────────────────────────────────────────────────────────────────────────┤
│ Executable   Status    Severity    Path                                  │
│ nvim         ✓ Found   error       /usr/bin/nvim                          │
│ git          ✓ Found   error       /usr/bin/git                           │
├───────────────────────────────────────────────────────────────────────────┤
│ Package: opencode                                                         │
├───────────────────────────────────────────────────────────────────────────┤
│ Executable   Status    Severity    Path                                  │
│ node         ✓ Found   warning     /usr/bin/node                          │
│ bun          ✗ Missing warning     Not in PATH                           │
├───────────────────────────────────────────────────────────────────────────┤
│ Package: zsh                                                              │
├───────────────────────────────────────────────────────────────────────────┤
│ Executable   Status    Severity    Path                                  │
│ zsh          ✓ Found   error       /usr/bin/zsh                           │
╰───────────────────────────────────────────────────────────────────────────╯

Summary: 0 errors, 1 warning, 4 passed
```

### Exit Codes

- **Exit code 0**: No error-severity executables are missing (warnings are acceptable)
- **Exit code 1**: One or more error-severity executables are missing

### How It Works

1. The doctor command loads your configuration and resolves the package dependency tree
2. For each package with `doctor.executables` defined, it checks if each executable exists in your system's PATH
3. Executable lookup uses `shutil.which()` for cross-platform compatibility (Linux, macOS, Windows)
4. Results are displayed in a formatted table grouped by package
5. A summary shows totals for errors, warnings, and passed checks

### Packages Without Doctor Config

Packages without a `doctor` configuration are still shown in the output with "No executable requirements":

```
$ dotman doctor

╭───────────────────────────────────────────────────────────────────────────╮
│ Doctor Check Results                                                      │
├───────────────────────────────────────────────────────────────────────────┤
│ Package: simple-config                                                    │
├───────────────────────────────────────────────────────────────────────────┤
│ Executable   Status    Severity    Path                                  │
│              No executable requirements                                   │
╰───────────────────────────────────────────────────────────────────────────╯

Summary: 0 errors, 0 warnings, 0 passed
```

### Best Practices

- Set `severity: error` for executables that are strictly required (e.g., `nvim`, `git`)
- Set `severity: warning` for executables that are optional or only needed for specific features
- Run `dotman doctor` before `dotman deploy` to catch missing dependencies early
- Use `--dry-run` with deploy to preview changes after fixing any doctor issues

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
        target: "~/.config/nvim" # Will be skipped, nvim-base processes first
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
          - "node_modules" # Ignore any path containing node_modules
          - "\\.git" # Ignore any path containing .git
          - ".*\\.log" # Ignore any .log files
```

### Smart Template Handling

When absorbing files, dotman automatically skips files that are template outputs. If a `.j2` template exists in your source (e.g., `config.conf.j2`), the rendered file in the target (e.g., `config.conf`) will not be absorbed to avoid duplicates.

## Hooks System

Dotman supports executing shell commands before and after deployments via a hooks system.

### Hook Types

- **pre_deploy** - Commands executed before deploying a package's files
- **post_deploy** - Commands executed after deploying a package's files

### Configuration

Define hooks in your package configuration:

```yaml
packages:
  nvim:
    depends: []
    files:
      - source: "nvim"
        target: "~/.config/nvim"
    hooks:
      pre_deploy:
        - "echo 'Starting neovim deployment'"
        - "mkdir -p ~/.config/nvim"
      post_deploy:
        - "echo 'Neovim deployment complete'"
        - "nvim --headless -c 'PlugInstall --sync' -c 'qall'"
```

### Template Variables in Hooks

Hook commands support Jinja2 template rendering with the following special variables:

- `{{package_name}}` - Name of the current package
- `{{dotfiles_dir}}` - Path to your dotfiles repository
- `{{target_dir}}` - Path to the target directory for the package
- `{{variable_name}}` - Any variables defined in your configuration

### Hook Examples

**Using package variables:**

```yaml
packages:
  nvim:
    variables:
      theme: "dracula"
    hooks:
      post_deploy:
        - "echo 'Theme set to {{theme}}'"
```

**Conditional execution with Jinja2:**

```yaml
packages:
  nvim:
    variables:
      debug: true
    hooks:
      pre_deploy:
        - "{% if debug %}echo 'Debug mode enabled'{% endif %}"
```

**Executing in target directory:**

```yaml
packages:
  myconfig:
    files:
      - source: "config"
        target: "~/.myconfig"
    hooks:
      post_deploy:
        - "{{dotfiles_dir}}/scripts/reload-config.sh"
```

### Hook Execution Behavior

- Hooks run in the order they are defined
- If a pre_deploy hook fails, deployment is aborted
- post_deploy hooks run even if file deployment has issues
- Commands are executed via shell, supporting pipes, redirects, and shell features
- Failed hooks raise a `HookExecutionError` with exit code and output details

### Dry Run and Hooks

When running with `--dry-run`, hooks are not executed (only displayed in the execution plan).

## Dependency Management

Define dependencies between packages to ensure correct deployment order.

### Basic Dependencies

```yaml
packages:
  base:
    files:
      - source: "base/files"
        target: "~/.config/base"

  nvim:
    depends: ["base"]
    files:
      - source: "nvim"
        target: "~/.config/nvim"
```

When deploying `nvim`, dotman will automatically deploy `base` first.

### Dependency Requirements

- All dependencies must be defined in `config.yaml`
- All dependencies must be enabled in `local.yaml`
- Dependencies are deployed in topological order (dependencies before dependents)

## Circular Dependency Detection

Dotman automatically detects circular dependencies between packages and prevents deployment with a clear error message.

Example circular dependency configuration (this will fail):

```yaml
packages:
  a:
    depends: ["b"]
    files:
      - source: "a"
        target: "~/.a"

  b:
    depends: ["a"]
    files:
      - source: "b"
        target: "~/.b"
```

When you try to deploy, you'll see:

```
Dependency error: Circular dependency detected: a -> b -> a
```

To fix, remove one of the dependency relationships.

## Deployment History

Dotman tracks all deployments in `.dotman/history.yaml` with unique deployment IDs.

### Viewing History

```bash
# View last 10 deployments (default)
dotman history

# View last 5 deployments
dotman history --limit 5
```

The history shows:
- **ID** - Unique deployment identifier (use for rollback)
- **Timestamp** - When the deployment occurred
- **Packages** - Which packages were deployed
- **Files** - Number of files processed
- **Type** - "Live" or "Dry Run"

### Deployment IDs

Each deployment gets a unique 8-character ID (UUID prefix) that you can use for rollback:

```bash
dotman history
# Example output:
# ID          Timestamp           Packages    Files    Type
# a1b2c3d4    2024-01-15 10:30    nvim, bash  15       Live
# e5f6g7h8    2024-01-14 09:15    vim         8        Live
```

## Rollback

Undo a previous deployment by restoring files from backups.

### Basic Rollback

```bash
# Rollback the most recent deployment
dotman rollback

# Rollback a specific deployment by ID
dotman rollback a1b2c3d4

# Preview rollback without making changes
dotman rollback --dry-run
```

### What Rollback Does

1. Removes symlinks created during the deployment
2. Restores original files from backups (if available)
3. Removes rendered template files
4. Removes the deployment from history

### Rollback Summary

After rollback, you'll see a summary:

```
Rollback summary:
  Processed: 15
  Skipped: 2
  Failed: 0
```

- **Processed** - Files successfully removed/restored
- **Skipped** - Files already removed (not present)
- **Failed** - Files that couldn't be restored

### Rollback Limitations

- Cannot rollback dry-run deployments (no changes were made)
- Backup files are cleaned up after successful restoration
- Rollback only affects files from the specified deployment
- Files created after the deployment will not be affected

### Example Workflow

```bash
# Deploy some packages
dotman deploy nvim vim

# Check history to get the deployment ID
dotman history
# ID: x9y8z7w6

# Oops, something went wrong!
# Rollback to restore previous state
dotman rollback x9y8z7w6
```

## Watch Mode

Automatically deploy dotfiles when source files are modified.

```bash
# Start watching for changes
dotman watch

# Watch will:
# - Monitor your dotfiles repository for changes
# - Deploy modified files automatically
# - Use platform-specific file system watchers (inotify on Linux, kqueue on macOS)
# - Debounce rapid changes to avoid excessive deployments
```

### How Watch Mode Works

1. Watches all configured package directories recursively
2. Detects file creation, modification, deletion, and movement
3. Waits for a quiet period (debounce) before deploying
4. Skips ACCESSED events to avoid unnecessary deployments
5. Press `Ctrl+C` to stop watching

### Platform Support

- **Linux**: Uses inotify for efficient kernel-level file system events
- **macOS/BSD**: Uses kqueue for optimal performance
- **Fallback**: Polling-based watcher if native APIs are unavailable

## Remote Repository Support

Clone, push, and pull dotfiles from GitHub, GitLab, or any Git remote.

### Cloning a Repository

```bash
# Clone using GitHub shorthand
dotman clone user/dotfiles

# Clone using full URL
dotman clone https://github.com/user/dotfiles.git

# Clone a specific branch
dotman clone user/dotfiles --branch develop

# Clone and initialize dotman
dotman clone user/dotfiles --init

# Shallow clone (faster, less history)
dotman clone user/dotfiles --shallow
```

### Pushing Changes

```bash
# Push to default remote (origin)
dotman push

# Push to a specific remote
dotman push origin

# Push a specific branch
dotman push origin main

# Push and set upstream tracking
dotman push --set-upstream origin develop
```

### Pulling Changes

```bash
# Pull from default remote (origin)
dotman pull

# Pull from a specific remote
dotman pull origin

# Pull a specific branch
dotman pull origin main
```

### URL Formats Supported

- `user/repo` - GitHub shorthand
- `github:user/repo` - Explicit GitHub prefix
- `gitlab:user/repo` - GitLab prefix
- Full HTTPS URLs
- SSH URLs (for push operations)

## Template Caching

Dotman caches compiled Jinja2 templates for faster repeated deployments.

### How Caching Works

1. First render: Template is compiled and cached
2. Subsequent renders: Cached version is used if source and variables haven't changed
3. Cache invalidation: Automatically invalidated when:
   - Source file modification time changes
   - Template variables change
   - Cache is explicitly cleared

### Cache Management

```bash
# Templates are automatically cached during deployment
# No manual management required

# Cache is invalidated when:
# - Source file is modified
# - Variables change
# - dotman deploy --force is used
```

### Performance Benefits

- Faster repeated deployments (skips template rendering)
- Reduced CPU usage for large template sets
- Smart detection of unchanged templates

## Package Include System

Compose configurations from multiple YAML files with the include system.

### Basic Includes

Include additional YAML files in your configuration:

```yaml
# config.yaml
includes:
  - "../shared/base.yaml"
  - "../os-specific/linux.yaml"

packages:
  myconfig:
    depends: []
    files:
      - source: "myconfig"
        target: "~/.myconfig"
```

### Circular Include Detection

Dotman automatically detects circular references in includes:

```yaml
# a.yaml
includes:
  - "b.yaml"

# b.yaml
includes:
  - "a.yaml"
```

This will produce an error:
```
CircularIncludeError: Circular reference detected: a.yaml -> b.yaml -> a.yaml
```

### Include Resolution

- Includes are resolved relative to the including file
- Nested includes are fully supported
- Each file is only processed once (prevents duplicate processing)
- Variables from included files are merged with precedence rules

## Multiple Repository Management

Register and manage multiple dotfiles repositories.

### Registering a Repository

```bash
# Register current directory as a named repository
dotman repo add work

# Register with a description
dotman repo add personal "My personal dotfiles"

# With remote URL detection
dotman repo add home
# Automatically detects if it's a git repo with remote
```

### Managing Repositories

```bash
# List all registered repositories
dotman repo list

# Show repository details
dotman repo show
dotman repo show work

# Set default repository
dotman repo default work

# Unregister a repository
dotman repo remove work
```

### Using Multiple Repositories

```bash
# Use a non-default repository
dotman --repo work deploy
dotman --repo personal status

# Each repository has its own config.yaml and history
```

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
│       ├── template_engine.py  # Jinja2 template rendering with caching
│       ├── hook_executor.py    # Hook execution for shell commands
│       ├── history.py          # Deployment history tracking
│       ├── exceptions.py       # Custom exceptions
│       ├── watcher.py          # File system watcher (inotify/kqueue/polling)
│       ├── remote.py           # Remote repository management
│       └── repository.py       # Multi-repository management
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_link_manager.py
│   ├── test_template_engine.py
│   ├── test_exceptions.py
│   ├── test_hooks.py
│   ├── test_cli_deploy.py
│   ├── test_cli_status.py
│   └── ...
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── AGENTS.md                   # Guidelines for AI agents
└── TODO.md                     # Development roadmap
```

## Safety Features

- **Automatic Backups** - Existing files are backed up before overwriting
- **Dry-Run Mode** - Preview all operations before execution
- **Status Checking** - Detects broken, missing, and conflicting symlinks
- **Confirmation Prompts** - Destructive operations can require confirmation
- **Deployment History** - Track all changes with unique IDs
- **Rollback Support** - Restore previous deployments from history

## Error Handling

Dotman uses a hierarchical exception system for clear and actionable error messages. All custom exceptions inherit from `DotmanError`.

### Exception Hierarchy

| Exception | Description |
|-----------|-------------|
| **DotmanError** | Base exception for all dotman errors |
| **ConfigError** | Configuration-related errors |
| ├─ ConfigNotFoundError | Configuration file not found |
| ├─ ConfigParseError | Error parsing configuration file |
| ├─ ConfigIncludeError | Error including configuration file |
| └─ CircularIncludeError | Circular reference in includes |
| **LinkError** | Symlink-related errors |
| ├─ LinkExistsError | Target already exists |
| └─ LinkTargetMissingError | Source file missing |
| **TemplateError** | Template-related errors |
| └─ TemplateRenderError | Error rendering template |
| **PackageError** | Package-related errors |
| ├─ PackageNotFoundError | Package not in config |
| └─ DependencyError | Dependency resolution errors |
| ├─ MissingDependencyError | Required dependency missing |
| └─ CircularDependencyError | Circular dependency detected |
| **HookError** | Hook-related errors |
| └─ HookExecutionError | Error executing hook |
| **HistoryError** | History-related errors |
| **RollbackError** | Rollback-related errors |
| **RemoteError** | Remote repository errors |
| ├─ RemoteCloneError | Error cloning repository |
| ├─ RemoteFetchError | Error fetching from remote |
| ├─ RemoteNotFoundError | Repository not found |
| ├─ RemoteAuthenticationError | Authentication failed |
| └─ RemotePushError | Error pushing to remote |
| **WatcherError** | File watcher errors |
| ├─ WatcherBackendError | Watcher backend error |
| └─ WatcherInitializationError | Watcher init failed |
| **RepositoryError** | Repository management errors |
| ├─ RepositoryNotFoundError | Repository not in registry |
| ├─ RepositoryAlreadyExistsError | Repository already exists |
| ├─ RepositoryPathError | Invalid repository path |
| └─ NothingToCommitError | No changes to commit |

### Catching Exceptions

All dotman exceptions can be caught as `DotmanError`:

```python
from dotman.exceptions import DotmanError

try:
    dotman.deploy()
except DotmanError as e:
    print(f"Error: {e}")
```

### Error Messages

Exception messages are designed to be user-friendly and actionable:

```
ConfigNotFoundError: Configuration file not found: /path/to/config.yaml
CircularDependencyError: Circular dependency detected: a -> b -> a
NothingToCommitError: No changes to commit in repository 'dotfiles'
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
