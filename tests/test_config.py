"""Unit tests for the Config class."""

import tempfile
from pathlib import Path

import pytest
import yaml

from dotman.config import Config, FileMapping, GlobalConfig, LocalConfig, PackageConfig
from dotman.exceptions import (
    CircularDependencyError,
    ConfigNotFoundError,
    ConfigParseError,
    MissingDependencyError,
)


class TestFileMapping:
    """Test FileMapping Pydantic model."""

    def test_file_mapping_creation(self):
        """Test creating a valid FileMapping with source and target."""
        mapping = FileMapping(source="~/.bashrc", target=".bashrc")
        assert mapping.source == "~/.bashrc"
        assert mapping.target == ".bashrc"

    def test_file_mapping_defaults(self):
        """Test FileMapping default values."""
        mapping = FileMapping(source="source", target="target")
        assert hasattr(mapping, "source")
        assert hasattr(mapping, "target")


class TestPackageConfig:
    """Test PackageConfig Pydantic model."""

    def test_package_config_empty(self):
        """Test PackageConfig with default empty values."""
        config = PackageConfig()
        assert config.depends == []
        assert config.files == []
        assert config.variables == {}

    def test_package_config_with_dependencies(self):
        """Test PackageConfig with dependency list."""
        config = PackageConfig(depends=["vim", "git"])
        assert config.depends == ["vim", "git"]

    def test_package_config_with_files(self):
        """Test PackageConfig with file mappings."""
        files = [
            FileMapping(source="a", target="b"),
            FileMapping(source="c", target="d"),
        ]
        config = PackageConfig(files=files)
        assert len(config.files) == 2

    def test_package_config_with_variables(self):
        """Test PackageConfig with custom variables."""
        variables = {"editor": "vim", "theme": "dark"}
        config = PackageConfig(variables=variables)
        assert config.variables == variables


class TestGlobalConfig:
    """Test GlobalConfig Pydantic model."""

    def test_global_config_defaults(self):
        """Test GlobalConfig default values."""
        config = GlobalConfig()
        assert config.settings.backup_dir == ".dotman/backups"
        assert config.settings.template_suffix == ".j2"
        assert config.variables == {}
        assert config.packages == {}

    def test_global_config_custom_settings(self):
        """Test GlobalConfig with custom settings."""
        from dotman.config import GlobalSettings

        config = GlobalConfig(
            settings=GlobalSettings(
                backup_dir="custom/backups",
                template_suffix=".template",
            )
        )
        assert config.settings.backup_dir == "custom/backups"
        assert config.settings.template_suffix == ".template"


class TestLocalConfig:
    """Test LocalConfig Pydantic model."""

    def test_local_config_defaults(self):
        """Test LocalConfig default values."""
        config = LocalConfig()
        assert config.packages == []
        assert config.variables == {}
        assert config.file_overrides == {}

    def test_local_config_with_packages(self):
        """Test LocalConfig with enabled packages."""
        config = LocalConfig(packages=["vim", "git"])
        assert config.packages == ["vim", "git"]


class TestConfigLoading:
    """Test Config class YAML loading functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_missing_config_raises_error(self):
        """Test that loading a non-existent config file raises ConfigNotFoundError."""
        config = Config(self.repo_dir)
        with pytest.raises(ConfigNotFoundError):
            config._load_yaml(self.dotman_dir / "missing.yaml")

    def test_load_empty_config_file(self):
        """Test loading an empty YAML file."""
        config_file = self.dotman_dir / "empty.yaml"
        config_file.write_text("")

        config = Config(self.repo_dir)
        result = config._load_yaml(config_file)
        assert result == {}

    def test_load_valid_yaml_file(self):
        """Test loading a valid YAML configuration."""
        config_file = self.dotman_dir / "config.yaml"
        data = {"key": "value", "number": 42}
        config_file.write_text(yaml.dump(data))

        config = Config(self.repo_dir)
        result = config._load_yaml(config_file)
        assert result == data

    def test_load_invalid_yaml_raises_parse_error(self):
        """Test that loading invalid YAML raises ConfigParseError."""
        config_file = self.dotman_dir / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [[[")

        config = Config(self.repo_dir)
        with pytest.raises(ConfigParseError):
            config._load_yaml(config_file)

    def test_load_global_config_missing_returns_default(self):
        """Test that missing global config returns empty GlobalConfig."""
        config = Config(self.repo_dir)
        global_config = config._load_global_config()
        assert isinstance(global_config, GlobalConfig)
        assert global_config.packages == {}

    def test_load_global_config_valid(self):
        """Test loading a valid global configuration."""
        config_file = self.dotman_dir / "config.yaml"
        config_data = {
            "settings": {"backup_dir": "custom/backups"},
            "variables": {"key": "value"},
            "packages": {"vim": {"depends": [], "files": [], "variables": {}}},
        }
        config_file.write_text(yaml.dump(config_data))

        config = Config(self.repo_dir)
        global_config = config._load_global_config()
        assert global_config.settings.backup_dir == "custom/backups"
        assert global_config.variables["key"] == "value"
        assert "vim" in global_config.packages

    def test_load_local_config_missing_returns_default(self):
        """Test that missing local config returns empty LocalConfig."""
        config = Config(self.repo_dir)
        local_config = config._load_local_config()
        assert isinstance(local_config, LocalConfig)
        assert local_config.packages == []

    def test_load_local_config_valid(self):
        """Test loading a valid local configuration."""
        config_file = self.dotman_dir / "local.yaml"
        config_data = {
            "packages": ["vim", "git"],
            "variables": {"theme": "dark"},
        }
        config_file.write_text(yaml.dump(config_data))

        config = Config(self.repo_dir)
        local_config = config._load_local_config()
        assert local_config.packages == ["vim", "git"]
        assert local_config.variables["theme"] == "dark"


class TestConfigInitialization:
    """Test Config initialization and setup."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_default_repo_directory(self):
        """Test Config uses current directory by default."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            config = Config()
            assert config.repo_dir == Path.cwd()
        finally:
            os.chdir(original_cwd)

    def test_custom_repo_directory(self):
        """Test Config accepts custom repository directory."""
        config = Config(self.repo_dir)
        assert config.repo_dir == self.repo_dir

    def test_dotman_directory_path(self):
        """Test Config calculates dotman directory correctly."""
        config = Config(self.repo_dir)
        expected_dotman_dir = self.repo_dir / ".dotman"
        assert config.dotman_dir == expected_dotman_dir

    def test_config_file_paths(self):
        """Test Config file paths are calculated correctly."""
        config = Config(self.repo_dir)
        dotman_dir = self.repo_dir / ".dotman"
        assert config.config_path == dotman_dir / "config.yaml"
        assert config.local_config_path == dotman_dir / "local.yaml"

    def test_is_initialized_false_when_no_dotman_dir(self):
        """Test is_initialized returns False when .dotman directory doesn't exist."""
        config = Config(self.repo_dir)
        assert config.is_initialized() is False

    def test_is_initialized_false_when_only_dotman_dir_exists(self):
        """Test is_initialized returns False when only .dotman directory exists."""
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()

        config = Config(self.repo_dir)
        assert config.is_initialized() is False

    def test_is_initialized_true_when_config_exists(self):
        """Test is_initialized returns True when config.yaml exists."""
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()
        config_file = self.dotman_dir / "config.yaml"
        config_file.write_text("")

        config = Config(self.repo_dir)
        assert config.is_initialized() is True


class TestConfigInit:
    """Test Config initialization functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_init_creates_dotman_directory(self):
        """Test init creates .dotman directory."""
        config = Config(self.repo_dir)
        dotman_dir = self.repo_dir / ".dotman"
        assert not dotman_dir.exists()
        config.init()
        assert config.dotman_dir.exists()

    def test_init_creates_config_yaml(self):
        """Test init creates config.yaml with default values."""
        config = Config(self.repo_dir)
        config.init()
        assert config.config_path.exists()

    def test_init_creates_local_yaml(self):
        """Test init creates local.yaml with default values."""
        config = Config(self.repo_dir)
        config.init()
        assert config.local_config_path.exists()

    def test_init_does_not_overwrite_existing_config(self):
        """Test init preserves existing configuration."""
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()
        existing_config = self.dotman_dir / "config.yaml"
        existing_content = "existing: config"
        existing_config.write_text(existing_content)

        config = Config(self.repo_dir)
        config.init()

        assert config.config_path.read_text() == existing_content


class TestConfigDependencyValidation:
    """Test Config dependency validation functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()

        # Set up a valid config with packages and dependencies
        self.config_file = self.dotman_dir / "config.yaml"
        self.local_file = self.dotman_dir / "local.yaml"

        config_data = {
            "packages": {
                "base": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
                "vim": {
                    "depends": ["base"],
                    "files": [],
                    "variables": {},
                },
                "git": {
                    "depends": ["base"],
                    "files": [],
                    "variables": {},
                },
                "full": {
                    "depends": ["vim", "git"],
                    "files": [],
                    "variables": {},
                },
            }
        }
        self.config_file.write_text(yaml.dump(config_data))

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_validate_no_packages(self):
        """Test validation passes with no enabled packages."""
        self.local_file.write_text(yaml.dump({"packages": []}))

        config = Config(self.repo_dir)
        config.validate_dependencies()  # Should not raise

    def test_validate_simple_package(self):
        """Test validation passes for simple package without dependencies."""
        self.local_file.write_text(yaml.dump({"packages": ["base"]}))

        config = Config(self.repo_dir)
        config.validate_dependencies()  # Should not raise

    def test_validate_package_with_valid_dependencies(self):
        """Test validation passes for package with valid dependencies."""
        self.local_file.write_text(yaml.dump({"packages": ["vim", "base"]}))

        config = Config(self.repo_dir)
        config.validate_dependencies()  # Should not raise

    def test_validate_missing_package_raises_error(self):
        """Test validation raises error for package not in config."""
        self.local_file.write_text(yaml.dump({"packages": ["nonexistent"]}))

        config = Config(self.repo_dir)
        with pytest.raises(MissingDependencyError) as exc_info:
            config.validate_dependencies()

        assert "nonexistent" in str(exc_info.value)

    def test_validate_missing_dependency_raises_error(self):
        """Test validation raises error for dependency not in config."""
        # Override config to have a dependency on undefined package
        config_data = {
            "packages": {
                "missing_dep": {
                    "depends": ["undefined"],
                    "files": [],
                    "variables": {},
                },
            }
        }
        self.config_file.write_text(yaml.dump(config_data))
        self.local_file.write_text(yaml.dump({"packages": ["missing_dep"]}))

        config = Config(self.repo_dir)
        with pytest.raises(MissingDependencyError) as exc_info:
            config.validate_dependencies()

        assert "undefined" in str(exc_info.value)

    def test_validate_disabled_dependency_raises_error(self):
        """Test validation raises error for disabled dependency."""
        self.local_file.write_text(yaml.dump({"packages": ["vim"]}))  # base not enabled

        config = Config(self.repo_dir)
        with pytest.raises(MissingDependencyError) as exc_info:
            config.validate_dependencies()

        assert "base" in str(exc_info.value)

    def test_validate_specific_packages(self):
        """Test validating specific package list instead of all enabled."""
        self.local_file.write_text(yaml.dump({"packages": ["base"]}))

        config = Config(self.repo_dir)
        config.validate_dependencies(["vim", "base"])  # Should not raise

    def test_validate_circular_dependency(self):
        """Test validation handles circular dependencies by detecting recursion."""
        # Override config to have circular dependencies
        config_data = {
            "packages": {
                "a": {
                    "depends": ["b"],
                    "files": [],
                    "variables": {},
                },
                "b": {
                    "depends": ["a"],
                    "files": [],
                    "variables": {},
                },
            }
        }
        self.config_file.write_text(yaml.dump(config_data))
        self.local_file.write_text(yaml.dump({"packages": ["a", "b"]}))

        config = Config(self.repo_dir)
        # Circular dependencies now raise a proper CircularDependencyError
        with pytest.raises(CircularDependencyError) as exc_info:
            config.validate_dependencies()
        assert "circular" in str(exc_info.value).lower()


class TestConfigPackageRetrieval:
    """Test Config package retrieval functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()

        config_data = {
            "packages": {
                "vim": {
                    "depends": ["base"],
                    "files": [{"source": "~/.vimrc", "target": ".vimrc"}],
                    "variables": {"theme": "dark"},
                },
                "git": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
            }
        }
        (self.dotman_dir / "config.yaml").write_text(yaml.dump(config_data))

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_enabled_packages(self):
        """Test getting list of enabled packages."""
        (self.dotman_dir / "local.yaml").write_text(
            yaml.dump({"packages": ["vim", "git"]})
        )

        config = Config(self.repo_dir)
        enabled = config.get_enabled_packages()

        assert enabled == ["vim", "git"]

    def test_get_enabled_packages_empty(self):
        """Test getting enabled packages when none are enabled."""
        (self.dotman_dir / "local.yaml").write_text(yaml.dump({"packages": []}))

        config = Config(self.repo_dir)
        enabled = config.get_enabled_packages()

        assert enabled == []

    def test_get_package(self):
        """Test getting a specific package configuration."""
        config = Config(self.repo_dir)
        package = config.get_package("vim")

        assert package is not None
        assert package.depends == ["base"]
        assert len(package.files) == 1

    def test_get_package_not_found(self):
        """Test getting a non-existent package returns None."""
        config = Config(self.repo_dir)
        package = config.get_package("nonexistent")

        assert package is None

    def test_get_all_packages_with_dependencies(self):
        """Test getting all packages including dependencies."""
        # Recreate config.yaml and local.yaml to ensure clean state
        config_data = {
            "variables": {"global_var": "global_value"},
            "packages": {
                "base": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
                "vim": {
                    "depends": ["base"],
                    "files": [{"source": "~/.vimrc", "target": ".vimrc"}],
                    "variables": {"editor": "vim", "local_override": "package_value"},
                },
                "git": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
            },
        }
        (self.dotman_dir / "config.yaml").write_text(yaml.dump(config_data))
        (self.dotman_dir / "local.yaml").write_text(
            yaml.dump({"packages": ["vim", "base"]})
        )

        config = Config(self.repo_dir)
        packages = config.get_all_packages_with_dependencies()

        # Should include vim and its dependency base
        assert "vim" in packages
        assert "base" in packages

    def test_get_all_packages_specific_list(self):
        """Test getting packages from specific list."""
        # Recreate config.yaml and local.yaml to ensure clean state
        config_data = {
            "variables": {"global_var": "global_value"},
            "packages": {
                "base": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
                "vim": {
                    "depends": ["base"],
                    "files": [{"source": "~/.vimrc", "target": ".vimrc"}],
                    "variables": {"editor": "vim", "local_override": "package_value"},
                },
                "git": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
            },
        }
        (self.dotman_dir / "config.yaml").write_text(yaml.dump(config_data))
        (self.dotman_dir / "local.yaml").write_text(yaml.dump({"packages": []}))

        config = Config(self.repo_dir)
        packages = config.get_all_packages_with_dependencies(["vim", "git", "base"])

        assert "vim" in packages
        assert "git" in packages
        assert "base" in packages


class TestConfigVariableResolution:
    """Test Config variable resolution functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()

        config_data = {
            "variables": {"global_var": "global_value"},
            "packages": {
                "base": {  # Add base package
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
                "vim": {
                    "depends": ["base"],
                    "files": [{"source": "~/.vimrc", "target": ".vimrc"}],
                    "variables": {"editor": "vim", "local_override": "package_value"},
                },
                "git": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                },
            },
        }
        (self.dotman_dir / "config.yaml").write_text(yaml.dump(config_data))

        local_data = {
            "variables": {"local_var": "local_value", "local_override": "local_value"},
        }
        (self.dotman_dir / "local.yaml").write_text(yaml.dump(local_data))

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_merged_variables_global_only(self):
        """Test getting merged variables with only global config."""
        (self.dotman_dir / "local.yaml").write_text(
            yaml.dump({"packages": [], "variables": {}})
        )

        config = Config(self.repo_dir)
        variables = config.get_merged_variables()

        assert variables["global_var"] == "global_value"

    def test_get_merged_variables_local_overrides_global(self):
        """Test that local variables override global variables."""
        config = Config(self.repo_dir)
        variables = config.get_merged_variables()

        assert variables["global_var"] == "global_value"
        assert variables["local_var"] == "local_value"
        assert variables["local_override"] == "local_value"

    def test_get_merged_variables_package_specific(self):
        """Test getting merged variables for specific package."""
        config = Config(self.repo_dir)
        variables = config.get_merged_variables("vim")

        # Should have global, local, and package variables
        assert variables["global_var"] == "global_value"
        assert variables["local_var"] == "local_value"
        assert variables["editor"] == "vim"
        assert variables["local_override"] == "package_value"  # Package overrides local

    def test_get_merged_variables_empty(self):
        """Test getting merged variables when no packages exist."""
        (self.dotman_dir / "config.yaml").write_text(yaml.dump({}))
        (self.dotman_dir / "local.yaml").write_text(yaml.dump({}))

        config = Config(self.repo_dir)
        variables = config.get_merged_variables()

        assert variables == {}


class TestConfigPaths:
    """Test Config path properties."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = Path(self.temp_dir)
        self.dotman_dir = self.repo_dir / ".dotman"
        self.dotman_dir.mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_dotfiles_dir(self):
        """Test dotfiles_dir property returns repo directory."""
        config = Config(self.repo_dir)
        assert config.dotfiles_dir == self.repo_dir

    def test_backup_dir(self):
        """Test backup_dir property returns correct path."""
        config = Config(self.repo_dir)
        expected_backup_dir = self.dotman_dir / "backups"
        assert config.backup_dir == expected_backup_dir

    def test_settings_property(self):
        """Test settings property returns GlobalSettings."""
        config = Config(self.repo_dir)
        settings = config.settings

        assert settings.backup_dir == ".dotman/backups"
        assert settings.template_suffix == ".j2"
