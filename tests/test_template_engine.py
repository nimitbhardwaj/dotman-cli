"""Unit tests for the TemplateEngine class."""

import tempfile
from pathlib import Path

import pytest

from dotman.exceptions import TemplateRenderError
from dotman.template_engine import TEMPLATE_PATTERN, TemplateEngine


class TestTemplateEngineInit:
    """Test TemplateEngine initialization."""

    def test_default_template_directory(self):
        """Test TemplateEngine uses None as default template directory."""
        engine = TemplateEngine()
        assert engine.template_dir is None

    def test_custom_template_directory(self):
        """Test TemplateEngine accepts custom template directory."""
        template_dir = Path("/custom/templates")
        engine = TemplateEngine(template_dir=template_dir)
        assert engine.template_dir == template_dir

    def test_env_lazy_initialization(self):
        """Test Jinja2 environment is created lazily."""
        engine = TemplateEngine()
        assert engine._env is None
        env = engine.env
        assert env is not None


class TestTemplateDetection:
    """Test template detection functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_is_template_with_jinja_syntax(self):
        """Test is_template returns True for files with Jinja2 syntax."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        assert engine.is_template(template_file) is True

    def test_is_template_with_control_syntax(self):
        """Test is_template returns True for Jinja2 control syntax."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("{% if condition %}true{% endif %}")

        assert engine.is_template(template_file) is True

    def test_is_template_with_comment_syntax(self):
        """Test is_template returns True for Jinja2 comment syntax."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("{# This is a comment #}")

        assert engine.is_template(template_file) is True

    def test_is_template_without_jinja_syntax(self):
        """Test is_template returns False for plain text files."""
        engine = TemplateEngine(self.template_dir)
        plain_file = self.template_dir / "plain.txt"
        plain_file.write_text("Hello world! This is plain text.")

        assert engine.is_template(plain_file) is False

    def test_is_template_empty_file(self):
        """Test is_template returns False for empty files."""
        engine = TemplateEngine(self.template_dir)
        empty_file = self.template_dir / "empty.txt"
        empty_file.write_text("")

        assert engine.is_template(empty_file) is False

    def test_is_template_malformed_jinja(self):
        """Test is_template handles malformed Jinja2 gracefully."""
        engine = TemplateEngine(self.template_dir)
        malformed_file = self.template_dir / "malformed.j2"
        malformed_file.write_text("{{ incomplete variable")

        # Should return False if Jinja2 syntax detection fails
        assert engine.is_template(malformed_file) is False

    def test_is_template_unreadable_file(self):
        """Test is_template handles unreadable files gracefully."""
        engine = TemplateEngine(self.template_dir)
        # File that exists but can't be read (permission denied simulation)
        # In practice, this might need mocking
        assert engine.is_template(Path("/nonexistent/file.j2")) is False


class TestTemplatePattern:
    """Test TEMPLATE_PATTERN regex functionality."""

    def test_pattern_matches_variable_syntax(self):
        """Test pattern matches variable interpolation syntax."""
        content = "Hello {{ name }}!"
        match = TEMPLATE_PATTERN.search(content)
        assert match is not None
        assert "{{ name }}" in match.group()

    def test_pattern_matches_control_syntax(self):
        """Test pattern matches control flow syntax."""
        content = "{% for item in items %}{{ item }}{% endfor %}"
        matches = TEMPLATE_PATTERN.findall(content)
        assert len(matches) > 0
        assert any("{% for" in m for m in matches)

    def test_pattern_matches_comment_syntax(self):
        """Test pattern matches comment syntax."""
        content = "{# This is a comment #}"
        match = TEMPLATE_PATTERN.search(content)
        assert match is not None

    def test_pattern_no_match_plain_text(self):
        """Test pattern doesn't match plain text."""
        content = "Hello world!"
        match = TEMPLATE_PATTERN.search(content)
        assert match is None

    def test_pattern_matches_multiple(self):
        """Test pattern finds multiple Jinja2 expressions."""
        content = "{{ name }} {{ age }} {{ city }}"
        matches = TEMPLATE_PATTERN.findall(content)
        assert len(matches) == 3


class TestStringRendering:
    """Test template string rendering functionality."""

    def test_render_simple_variables(self):
        """Test rendering template string with simple variables."""
        engine = TemplateEngine()
        content = "Hello {{ name }}!"
        variables = {"name": "World"}

        result = engine.render_string(content, variables)

        assert result == "Hello World!"

    def test_render_multiple_variables(self):
        """Test rendering with multiple variables."""
        engine = TemplateEngine()
        content = "{{ greeting }} {{ name }}, your score is {{ score }}."
        variables = {"greeting": "Hello", "name": "Alice", "score": 95}

        result = engine.render_string(content, variables)

        assert result == "Hello Alice, your score is 95."

    def test_render_with_conditionals(self):
        """Test rendering with Jinja2 conditionals."""
        engine = TemplateEngine()
        content = "{% if admin %}Admin{% else %}User{% endif %}"
        variables = {"admin": True}

        result = engine.render_string(content, variables)

        assert result == "Admin"

    def test_render_with_loops(self):
        """Test rendering with Jinja2 loops."""
        engine = TemplateEngine()
        content = "{% for item in items %}{{ item }},{% endfor %}"
        variables = {"items": ["apple", "banana", "cherry"]}

        result = engine.render_string(content, variables)

        assert result == "apple,banana,cherry,"

    def test_render_missing_variable_renders_empty(self):
        """Test rendering with missing variable renders empty string by default."""
        engine = TemplateEngine()
        content = "Hello {{ name }}!"
        variables = {}  # Missing 'name'

        # Jinja2 renders missing variables as empty strings by default
        result = engine.render_string(content, variables)
        assert result == "Hello !"

    def test_render_syntax_error_raises_error(self):
        """Test rendering with syntax error raises error."""
        engine = TemplateEngine()
        content = "{% if condition %}true{% endif invalid syntax"
        variables = {"condition": True}

        with pytest.raises(TemplateRenderError) as exc_info:
            engine.render_string(content, variables)

        assert "Template error" in str(exc_info.value)

    def test_render_complex_template(self):
        """Test rendering complex template with multiple features."""
        engine = TemplateEngine()
        content = """
{% for user in users %}
  {{ user.name }} - {{ user.role }}
{% endfor %}
Total: {{ users|length }} users
"""
        variables = {
            "users": [
                {"name": "Alice", "role": "admin"},
                {"name": "Bob", "role": "developer"},
            ]
        }

        result = engine.render_string(content, variables)

        assert "Alice - admin" in result
        assert "Bob - developer" in result
        assert "Total: 2 users" in result


class TestFileRendering:
    """Test template file rendering functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_render_file_success(self):
        """Test rendering a template file successfully."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        result = engine.render_file(template_file, {"name": "World"})

        assert result == "Hello World!"

    def test_render_file_to_output(self):
        """Test rendering template to output file."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")
        output_file = Path(self.temp_dir) / "output.txt"

        result = engine.render_file(
            template_file, {"name": "World"}, output=output_file
        )

        assert result == "Hello World!"
        assert output_file.exists()
        assert output_file.read_text() == "Hello World!"

    def test_render_file_creates_parent_directories(self):
        """Test rendering creates parent directories for output."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")
        output_file = Path(self.temp_dir) / "nested" / "deep" / "output.txt"

        engine.render_file(template_file, {"name": "World"}, output=output_file)

        assert output_file.exists()

    def test_render_missing_file_raises_error(self):
        """Test rendering non-existent file raises error."""
        engine = TemplateEngine(self.template_dir)
        missing_file = self.template_dir / "missing.j2"

        with pytest.raises(TemplateRenderError) as exc_info:
            engine.render_file(missing_file, {})

        assert "Error reading template" in str(exc_info.value)

    def test_render_file_with_conditionals(self):
        """Test rendering file with conditional logic."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "config.j2"
        template_file.write_text("debug = {% if debug %}true{% else %}false{% endif %}")
        output_file = Path(self.temp_dir) / "config.txt"

        result = engine.render_file(template_file, {"debug": True}, output=output_file)

        assert result == "debug = true"
        assert output_file.read_text() == "debug = true"


class TestVariableExtraction:
    """Test variable extraction functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_template_variables(self):
        """Test extracting variables from template file."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}, your score is {{ score }}!")

        variables = engine.get_template_variables(template_file)

        assert "name" in variables
        assert "score" in variables

    def test_get_template_variables_complex(self):
        """Test extracting variables from complex template."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "complex.j2"
        template_file.write_text("""
{% for user in users %}
  {{ user.name }} ({{ user.email }})
{% endfor %}
Total: {{ total }}
""")

        variables = engine.get_template_variables(template_file)

        assert "users" in variables
        assert "total" in variables

    def test_get_string_variables(self):
        """Test extracting variables from template string."""
        engine = TemplateEngine()
        content = "Hello {{ name }}, welcome to {{ place }}!"

        variables = engine.get_string_variables(content)

        assert "name" in variables
        assert "place" in variables

    def test_get_string_variables_empty(self):
        """Test extracting variables from plain text."""
        engine = TemplateEngine()
        content = "Hello world, this is plain text."

        variables = engine.get_string_variables(content)

        assert len(variables) == 0

    def test_get_string_variables_syntax_error(self):
        """Test handling syntax errors during variable extraction."""
        engine = TemplateEngine()
        content = "{{ incomplete syntax {% endif %}"

        variables = engine.get_string_variables(content)

        # Should return empty set instead of crashing
        assert variables == set()

    def test_get_template_variables_unreadable(self):
        """Test handling unreadable files during variable extraction."""
        engine = TemplateEngine(self.template_dir)

        variables = engine.get_template_variables(Path("/nonexistent/file.j2"))

        assert variables == set()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_render_empty_string(self):
        """Test rendering empty string."""
        engine = TemplateEngine()
        result = engine.render_string("", {})
        assert result == ""

    def test_render_string_without_variables(self):
        """Test rendering string without variable placeholders."""
        engine = TemplateEngine()
        content = "This is plain text with no variables."
        result = engine.render_string(content, {})
        assert result == content

    def test_render_with_whitespace_control(self):
        """Test rendering with Jinja2 whitespace control."""
        engine = TemplateEngine()
        content = "{%- if true -%}content{%- endif -%}"
        result = engine.render_string(content, {})
        assert result == "content"

    def test_render_complex_nested_conditionals(self):
        """Test rendering with nested conditionals."""
        engine = TemplateEngine()
        content = """
{% if a %}
  {% if b %}
    Both a and b
  {% else %}
    a but not b
  {% endif %}
{% else %}
  Not a
{% endif %}
"""
        result = engine.render_string(content, {"a": True, "b": False})
        assert "a but not b" in result

    def test_template_engine_with_template_directory(self):
        """Test TemplateEngine with custom template directory."""
        template_dir = Path(tempfile.mkdtemp())
        try:
            engine = TemplateEngine(template_dir)
            # Should use FileSystemLoader when template_dir is set
            assert engine.env.loader is not None
        finally:
            import shutil

            shutil.rmtree(template_dir)

    def test_template_engine_without_template_directory(self):
        """Test TemplateEngine without template directory."""
        engine = TemplateEngine()
        # Should work without FileSystemLoader
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_special_characters(self):
        """Test rendering template with special characters."""
        engine = TemplateEngine()
        content = "Special: {{ text }}"
        result = engine.render_string(content, {"text": "Hello\nWorld\t!"})
        assert result == "Special: Hello\nWorld\t!"

    def test_render_unicode_content(self):
        """Test rendering template with unicode content."""
        engine = TemplateEngine()
        content = "Unicode: {{ text }}"
        result = engine.render_string(content, {"text": "Hello 世界 🌍"})
        assert "世界" in result
        assert "🌍" in result
