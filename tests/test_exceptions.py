"""Unit tests for the exception hierarchy."""

import pytest

from dotman.exceptions import (
    ConfigError,
    ConfigNotFoundError,
    ConfigParseError,
    DependencyError,
    DotmanError,
    LinkError,
    LinkExistsError,
    LinkTargetMissingError,
    MissingDependencyError,
    PackageError,
    PackageNotFoundError,
    TemplateError,
    TemplateRenderError,
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_dotman_error_is_base(self):
        """Test DotmanError is the base exception class."""
        error = DotmanError("Base error")
        assert isinstance(error, Exception)
        assert isinstance(error, DotmanError)

    def test_config_error_inherits_from_dotman(self):
        """Test ConfigError inherits from DotmanError."""
        error = ConfigError("Config error")
        assert isinstance(error, DotmanError)
        assert isinstance(error, ConfigError)

    def test_config_not_found_error_inherits_from_config(self):
        """Test ConfigNotFoundError inherits from ConfigError."""
        error = ConfigNotFoundError("Config not found")
        assert isinstance(error, ConfigError)
        assert isinstance(error, DotmanError)

    def test_config_parse_error_inherits_from_config(self):
        """Test ConfigParseError inherits from ConfigError."""
        error = ConfigParseError("Config parse error")
        assert isinstance(error, ConfigError)
        assert isinstance(error, DotmanError)

    def test_link_error_inherits_from_dotman(self):
        """Test LinkError inherits from DotmanError."""
        error = LinkError("Link error")
        assert isinstance(error, DotmanError)
        assert isinstance(error, LinkError)

    def test_link_exists_error_inherits_from_link(self):
        """Test LinkExistsError inherits from LinkError."""
        error = LinkExistsError("Link exists error")
        assert isinstance(error, LinkError)
        assert isinstance(error, DotmanError)

    def test_link_target_missing_error_inherits_from_link(self):
        """Test LinkTargetMissingError inherits from LinkError."""
        error = LinkTargetMissingError("Link target missing error")
        assert isinstance(error, LinkError)
        assert isinstance(error, DotmanError)

    def test_template_error_inherits_from_dotman(self):
        """Test TemplateError inherits from DotmanError."""
        error = TemplateError("Template error")
        assert isinstance(error, DotmanError)
        assert isinstance(error, TemplateError)

    def test_template_render_error_inherits_from_template(self):
        """Test TemplateRenderError inherits from TemplateError."""
        error = TemplateRenderError("Template render error")
        assert isinstance(error, TemplateError)
        assert isinstance(error, DotmanError)

    def test_package_error_inherits_from_dotman(self):
        """Test PackageError inherits from DotmanError."""
        error = PackageError("Package error")
        assert isinstance(error, DotmanError)
        assert isinstance(error, PackageError)

    def test_package_not_found_error_inherits_from_package(self):
        """Test PackageNotFoundError inherits from PackageError."""
        error = PackageNotFoundError("Package not found error")
        assert isinstance(error, PackageError)
        assert isinstance(error, DotmanError)

    def test_dependency_error_inherits_from_package(self):
        """Test DependencyError inherits from PackageError."""
        error = DependencyError("Dependency error")
        assert isinstance(error, PackageError)
        assert isinstance(error, DotmanError)

    def test_missing_dependency_error_inherits_from_dependency(self):
        """Test MissingDependencyError inherits from DependencyError."""
        error = MissingDependencyError("Missing dependency error")
        assert isinstance(error, DependencyError)
        assert isinstance(error, PackageError)
        assert isinstance(error, DotmanError)


class TestExceptionMessages:
    """Test exception error messages."""

    def test_dotman_error_message(self):
        """Test DotmanError message content."""
        error = DotmanError("Test error message")
        assert str(error) == "Test error message"

    def test_config_not_found_error_message(self):
        """Test ConfigNotFoundError message formatting."""
        error = ConfigNotFoundError("/path/to/config.yaml")
        assert "/path/to/config.yaml" in str(error)

    def test_config_parse_error_message(self):
        """Test ConfigParseError message formatting."""
        error = ConfigParseError("YAML parsing failed")
        assert "YAML parsing failed" in str(error)

    def test_link_exists_error_message(self):
        """Test LinkExistsError message formatting."""
        error = LinkExistsError("/path/to/target")
        assert "/path/to/target" in str(error)

    def test_link_target_missing_error_message(self):
        """Test LinkTargetMissingError message formatting."""
        error = LinkTargetMissingError("/path/to/source")
        assert "/path/to/source" in str(error)

    def test_template_render_error_message(self):
        """Test TemplateRenderError message formatting."""
        error = TemplateRenderError("Variable 'unknown' is undefined")
        assert "Variable 'unknown' is undefined" in str(error)


class TestExceptionCatching:
    """Test exception catching and handling."""

    def test_catch_base_exception(self):
        """Test catching base DotmanError catches all exceptions."""
        with pytest.raises(DotmanError):
            raise ConfigNotFoundError("Config file missing")

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        # Should be able to catch specific exception
        with pytest.raises(ConfigNotFoundError):
            raise ConfigNotFoundError("Config file missing")

    def test_exception_chaining(self):
        """Test exception chaining functionality."""
        try:
            try:
                raise ConfigNotFoundError("Config not found")
            except ConfigNotFoundError as e:
                raise ConfigParseError("Config parse error") from e
        except ConfigParseError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ConfigNotFoundError)

    def test_raise_and_catch_different_levels(self):
        """Test raising and catching at different hierarchy levels."""
        # Should be able to catch at different levels of inheritance
        with pytest.raises(ConfigError):
            raise ConfigNotFoundError("Config not found")

        with pytest.raises(DotmanError):
            raise ConfigNotFoundError("Config not found")

    def test_raise_link_error_catch_base(self):
        """Test raising LinkError and catching with base DotmanError."""
        with pytest.raises(DotmanError):
            raise LinkExistsError("Link exists")


class TestExceptionEquality:
    """Test exception equality and comparison."""

    def test_same_exception_messages_equal(self):
        """Test exceptions with same messages are equal."""
        error1 = DotmanError("Test message")
        error2 = DotmanError("Test message")
        # Exceptions with same message are not necessarily equal
        # but str() comparison should work
        assert str(error1) == str(error2)

    def test_different_exception_types_not_equal(self):
        """Test different exception types are not equal."""
        error1 = ConfigError("Same message")
        error2 = LinkError("Same message")
        # They are different types
        assert not isinstance(error1, LinkError)
        assert not isinstance(error2, ConfigError)

    def test_exception_with_cause(self):
        """Test exception with cause maintains chain."""
        try:
            try:
                raise ValueError("Original")
            except ValueError as e:
                raise MissingDependencyError("Missing dep") from e
        except MissingDependencyError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)


class TestExceptionUsage:
    """Test exception usage in realistic scenarios."""

    def test_config_file_not_found(self):
        """Test ConfigNotFoundError for missing configuration file."""
        with pytest.raises(ConfigNotFoundError) as exc_info:
            raise ConfigNotFoundError("/dotman/config.yaml")

        assert "config.yaml" in str(exc_info.value)

    def test_invalid_yaml_format(self):
        """Test ConfigParseError for invalid YAML syntax."""
        with pytest.raises(ConfigParseError) as exc_info:
            raise ConfigParseError("mapping values are not allowed here")

        assert "mapping values are not allowed here" in str(exc_info.value)

    def test_symlink_target_already_exists(self):
        """Test LinkExistsError when target file already exists."""
        with pytest.raises(LinkExistsError) as exc_info:
            raise LinkExistsError("/home/user/.bashrc")

        assert ".bashrc" in str(exc_info.value)

    def test_symlink_source_missing(self):
        """Test LinkTargetMissingError when source file doesn't exist."""
        with pytest.raises(LinkTargetMissingError) as exc_info:
            raise LinkTargetMissingError("/dotfiles/missing_file")

        assert "missing_file" in str(exc_info.value)

    def test_template_variable_undefined(self):
        """Test TemplateRenderError for undefined template variables."""
        with pytest.raises(TemplateRenderError) as exc_info:
            raise TemplateRenderError("Undefined variable: 'username'")

        assert "username" in str(exc_info.value)

    def test_template_syntax_error(self):
        """Test TemplateRenderError for Jinja2 syntax errors."""
        with pytest.raises(TemplateRenderError) as exc_info:
            raise TemplateRenderError("unexpected 'end of template'")

        assert "end of template" in str(exc_info.value)

    def test_package_not_in_config(self):
        """Test PackageNotFoundError for missing package configuration."""
        with pytest.raises(PackageNotFoundError) as exc_info:
            raise PackageNotFoundError("vim-config")

        assert "vim-config" in str(exc_info.value)

    def test_missing_dependency(self):
        """Test MissingDependencyError for missing package dependencies."""
        with pytest.raises(MissingDependencyError) as exc_info:
            raise MissingDependencyError(
                "Package 'vim' depends on 'base', but 'base' is not defined"
            )

        assert "vim" in str(exc_info.value)
        assert "base" in str(exc_info.value)


class TestExceptionProperties:
    """Test exception properties and attributes."""

    def test_exception_args(self):
        """Test exception args property."""
        error = ConfigNotFoundError("test message")
        assert error.args[0] == "test message"

    def test_exception_with_multiple_args(self):
        """Test exception with multiple arguments."""
        error = MissingDependencyError("pkg1", "pkg2", "pkg3")
        assert len(error.args) == 3
        assert "pkg1" in error.args
        assert "pkg2" in error.args
        assert "pkg3" in error.args

    def test_exception_traceback(self):
        """Test exception contains traceback information."""
        try:
            try:
                raise ConfigNotFoundError("Test")
            except ConfigNotFoundError:
                # Re-raise to capture traceback
                raise
        except ConfigNotFoundError:
            import sys

            # Should have traceback
            assert sys.exc_info()[2] is not None


class TestExceptionInheritance:
    """Test detailed exception inheritance scenarios."""

    def test_can_catch_as_parent_class(self):
        """Test exceptions can be caught as parent class."""
        # Should be able to catch ConfigError instead of specific type
        with pytest.raises(ConfigError):
            raise ConfigNotFoundError("config.yaml")

        with pytest.raises(ConfigError):
            raise ConfigParseError("invalid yaml")

        # Should be able to catch LinkError instead of specific type
        with pytest.raises(LinkError):
            raise LinkExistsError("target")

        with pytest.raises(LinkError):
            raise LinkTargetMissingError("source")

        # Should be able to catch TemplateError instead of specific type
        with pytest.raises(TemplateError):
            raise TemplateRenderError("render failed")

    def test_exception_mro_is_correct(self):
        """Test exception Method Resolution Order is correct."""
        # Check MRO for MissingDependencyError
        mro = MissingDependencyError.__mro__
        expected_order = (
            MissingDependencyError,
            DependencyError,
            PackageError,
            DotmanError,
            Exception,
            BaseException,
            object,
        )
        # Convert to list for comparison since __mro__ is a tuple
        assert list(mro[:7]) == list(expected_order)

    def test_can_raise_from_different_module(self):
        """Test exceptions can be raised from different modules consistently."""
        # This tests that all exceptions follow the same pattern
        exceptions = [
            (ConfigNotFoundError, "config.yaml"),
            (LinkExistsError, "/path/to/target"),
            (TemplateRenderError, "template error"),
            (MissingDependencyError, "missing dep"),
        ]

        for exc_class, message in exceptions:
            with pytest.raises(exc_class):
                raise exc_class(message)

            # Check that they can all be caught as DotmanError
            try:
                raise exc_class(message)
            except DotmanError:
                pass  # Expected
