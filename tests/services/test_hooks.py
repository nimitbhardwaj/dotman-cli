"""Unit tests for hook execution functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from dotman.core.config import Config, HookConfig, PackageConfig
from dotman.core.exceptions import HookExecutionError
from dotman.services.hook_executor import HookExecutor


class TestHookConfig:
    """Test HookConfig Pydantic model."""

    def test_hook_config_empty(self):
        """Test HookConfig with default empty values."""
        config = HookConfig()
        assert config.pre_deploy == []
        assert config.post_deploy == []

    def test_hook_config_with_pre_deploy(self):
        """Test HookConfig with pre-deploy hooks."""
        hooks = HookConfig(pre_deploy=["echo hello", "ls -la"])
        assert len(hooks.pre_deploy) == 2
        assert hooks.pre_deploy[0] == "echo hello"

    def test_hook_config_with_post_deploy(self):
        """Test HookConfig with post-deploy hooks."""
        hooks = HookConfig(post_deploy=["echo done", "notify-send done"])
        assert len(hooks.post_deploy) == 2
        assert hooks.post_deploy[0] == "echo done"

    def test_hook_config_with_both(self):
        """Test HookConfig with both pre and post deploy hooks."""
        hooks = HookConfig(pre_deploy=["echo starting"], post_deploy=["echo finished"])
        assert len(hooks.pre_deploy) == 1
        assert len(hooks.post_deploy) == 1


class TestPackageConfigWithHooks:
    """Test PackageConfig with hooks field."""

    def test_package_config_empty_hooks(self):
        """Test PackageConfig with default empty hooks."""
        config = PackageConfig()
        assert config.hooks.pre_deploy == []
        assert config.hooks.post_deploy == []

    def test_package_config_with_hooks(self):
        """Test PackageConfig with hooks defined."""
        hooks = HookConfig(pre_deploy=["echo pre"], post_deploy=["echo post"])
        config = PackageConfig(hooks=hooks)
        assert len(config.hooks.pre_deploy) == 1
        assert len(config.hooks.post_deploy) == 1

    def test_package_config_with_hooks_dict(self):
        """Test PackageConfig with hooks defined via dict."""
        config = PackageConfig(
            hooks={"pre_deploy": ["echo pre"], "post_deploy": ["echo post"]}
        )
        assert len(config.hooks.pre_deploy) == 1
        assert len(config.hooks.post_deploy) == 1


class TestHookExecutor:
    """Test HookExecutor class."""

    def test_dry_run_does_not_execute(self):
        """Test that dry_run mode doesn't execute commands."""
        executor = HookExecutor(dry_run=True)
        executor.execute_hook("echo test", "test_pkg", "pre_deploy")
        # No exception means success

    def test_execute_simple_command(self):
        """Test executing a simple shell command."""
        executor = HookExecutor(dry_run=False)
        executor.execute_hook("echo hello", "test_pkg", "pre_deploy")

    def test_execute_command_with_variables(self):
        """Test executing a command with variable expansion."""
        executor = HookExecutor(dry_run=False, cwd=Path.cwd())
        executor.execute_hook(
            "echo {{name}}", "test_pkg", "pre_deploy", {"name": "world"}
        )

    def test_execute_command_failure(self):
        """Test that command failure raises HookExecutionError."""
        executor = HookExecutor(dry_run=False)
        with pytest.raises(HookExecutionError):
            executor.execute_hook("exit 1", "test_pkg", "pre_deploy")

    def test_execute_multiple_hooks(self):
        """Test executing multiple hooks."""
        executor = HookExecutor(dry_run=False)
        executor.execute_hooks(["echo first", "echo second"], "test_pkg", "pre_deploy")

    def test_render_template(self):
        """Test template rendering with Jinja2."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "echo {{greeting}} {{name}}",
            "test_pkg",
            {"greeting": "Hello", "name": "World"},
            None,
            None,
        )
        assert result == "echo Hello World"

    def test_render_template_no_match(self):
        """Test template rendering with no matching variables uses Jinja2 defaults."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "echo {{unknown}}", "test_pkg", {}, None, None
        )
        assert result == "echo "

    def test_render_template_none(self):
        """Test template rendering with None variables."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template("echo test", "test_pkg", None, None, None)
        assert result == "echo test"

    def test_render_template_with_package_name(self):
        """Test template rendering with package_name special variable."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "echo {{package_name}}", "my_package", {}, None, None
        )
        assert result == "echo my_package"

    def test_render_template_with_dotfiles_dir(self):
        """Test template rendering with dotfiles_dir special variable."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "echo {{dotfiles_dir}}", "test_pkg", {}, Path("/home/user/dotfiles"), None
        )
        assert result == "echo /home/user/dotfiles"

    def test_render_template_with_target_dir(self):
        """Test template rendering with target_dir special variable."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "echo {{target_dir}}", "test_pkg", {}, None, Path("/home/user")
        )
        assert result == "echo /home/user"

    def test_render_template_with_all_special_vars(self):
        """Test template rendering with all special variables."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "Deploying {{package_name}} from {{dotfiles_dir}} to {{target_dir}}",
            "my_pkg",
            {},
            Path("/dots"),
            Path("/home/user"),
        )
        assert result == "Deploying my_pkg from /dots to /home/user"

    def test_render_template_with_jinja2_filters(self):
        """Test that Jinja2 filters work in templates."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "echo {{name|upper}}", "test_pkg", {"name": "hello"}, None, None
        )
        assert result == "echo HELLO"

    def test_render_template_with_jinja2_conditionals(self):
        """Test that Jinja2 conditionals work in templates."""
        executor = HookExecutor(dry_run=True)
        result = executor._render_template(
            "{% if debug %}debug mode{% else %}production{% endif %}",
            "test_pkg",
            {"debug": True},
            None,
            None,
        )
        assert result == "debug mode"

    def test_custom_cwd(self):
        """Test executing command in custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = HookExecutor(dry_run=False, cwd=Path(tmpdir))
            executor.execute_hook("pwd", "test_pkg", "pre_deploy")


class TestHookConfigInConfigFile:
    """Test loading hooks from configuration files."""

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

    def test_load_package_with_hooks(self):
        """Test loading a package with hooks from config."""
        config_data = {
            "packages": {
                "test_pkg": {
                    "depends": [],
                    "files": [],
                    "variables": {},
                    "hooks": {
                        "pre_deploy": ["echo pre-deploy"],
                        "post_deploy": ["echo post-deploy"],
                    },
                }
            }
        }
        (self.dotman_dir / "config.yaml").write_text(yaml.dump(config_data))
        (self.dotman_dir / "local.yaml").write_text(
            yaml.dump({"packages": ["test_pkg"]})
        )

        config = Config(self.repo_dir)
        pkg = config.get_package("test_pkg")

        assert pkg is not None
        assert len(pkg.hooks.pre_deploy) == 1
        assert len(pkg.hooks.post_deploy) == 1
        assert pkg.hooks.pre_deploy[0] == "echo pre-deploy"

    def test_load_package_without_hooks(self):
        """Test loading a package without hooks (backwards compatibility)."""
        config_data = {
            "packages": {"test_pkg": {"depends": [], "files": [], "variables": {}}}
        }
        (self.dotman_dir / "config.yaml").write_text(yaml.dump(config_data))
        (self.dotman_dir / "local.yaml").write_text(
            yaml.dump({"packages": ["test_pkg"]})
        )

        config = Config(self.repo_dir)
        pkg = config.get_package("test_pkg")

        assert pkg is not None
        assert pkg.hooks.pre_deploy == []
        assert pkg.hooks.post_deploy == []
