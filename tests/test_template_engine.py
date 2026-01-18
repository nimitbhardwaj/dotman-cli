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


class TestCacheStateDetection:
    """Test cache state detection and invalidation functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_cache_status_not_cached(self):
        """Test cache status returns not_cached for uncached source."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        is_valid, reason = engine.get_cache_status(template_file, {"name": "World"})

        assert is_valid is False
        assert reason == "not_cached"

    def test_get_cache_status_source_not_exists(self):
        """Test cache status returns source_not_exists for missing source."""
        engine = TemplateEngine(self.template_dir)
        missing_file = self.template_dir / "missing.j2"

        is_valid, reason = engine.get_cache_status(missing_file, {"name": "World"})

        assert is_valid is False
        assert reason == "source_not_exists"

    def test_cache_after_render(self):
        """Test that rendering caches the result."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})

        is_valid, reason = engine.get_cache_status(template_file, {"name": "World"})

        assert is_valid is True
        assert reason == "valid"

    def test_get_cache_status_variables_changed(self):
        """Test cache status detects variable changes."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})

        is_valid, reason = engine.get_cache_status(template_file, {"name": "Alice"})

        assert is_valid is False
        assert reason == "variables_changed"

    def test_get_cache_status_source_modified(self):
        """Test cache status detects source file modification."""
        import time

        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})

        time.sleep(0.01)
        template_file.write_text("Hello {{ name }} from modified!")

        is_valid, reason = engine.get_cache_status(template_file, {"name": "World"})

        assert is_valid is False
        assert reason == "source_modified"

    def test_invalidate_cache_specific_source(self):
        """Test invalidating cache for a specific source."""
        engine = TemplateEngine(self.template_dir)
        template_file1 = self.template_dir / "template1.j2"
        template_file2 = self.template_dir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file2, {"name": "World"})

        assert len(engine._cache) == 2

        count = engine.invalidate_cache(template_file1)

        assert count == 1
        assert len(engine._cache) == 1
        assert template_file2 in engine._cache
        assert template_file1 not in engine._cache

    def test_invalidate_cache_all_sources(self):
        """Test invalidating all cached sources."""
        engine = TemplateEngine(self.template_dir)
        template_file1 = self.template_dir / "template1.j2"
        template_file2 = self.template_dir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file2, {"name": "World"})

        assert len(engine._cache) == 2

        count = engine.invalidate_cache()

        assert count == 2
        assert len(engine._cache) == 0

    def test_invalidate_cache_nonexistent_source(self):
        """Test invalidating cache for a non-cached source returns 0."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        count = engine.invalidate_cache(template_file)

        assert count == 0

    def test_get_cached_content(self):
        """Test retrieving cached content."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        result = engine.get_cached_content(template_file)

        assert result is None

        engine.render_file(template_file, {"name": "World"})

        result = engine.get_cached_content(template_file)

        assert result == "Hello World!"

    def test_render_uses_cache(self):
        """Test that render uses cached result when valid."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        result1 = engine.render_file(template_file, {"name": "World"})
        result2 = engine.render_file(template_file, {"name": "World"})

        assert result1 == result2 == "Hello World!"
        assert len(engine._cache) == 1

    def test_render_invalidates_on_source_change(self):
        """Test that render re-renders when source changes."""
        import time

        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        result1 = engine.render_file(template_file, {"name": "World"})

        time.sleep(0.01)
        template_file.write_text("Hi {{ name }}!")

        result2 = engine.render_file(template_file, {"name": "World"})

        assert result1 == "Hello World!"
        assert result2 == "Hi World!"

    def test_variables_hash_different_for_different_vars(self):
        """Test that variables hash differs for different variables."""
        engine = TemplateEngine(self.template_dir)

        hash1 = engine._get_variables_hash({"name": "World", "age": 30})
        hash2 = engine._get_variables_hash({"name": "World", "age": 25})
        hash3 = engine._get_variables_hash({"name": "Alice", "age": 30})

        assert hash1 != hash2
        assert hash1 != hash3

    def test_variables_hash_same_for_same_vars(self):
        """Test that variables hash is same for same variables."""
        engine = TemplateEngine(self.template_dir)

        hash1 = engine._get_variables_hash({"name": "World", "age": 30})
        hash2 = engine._get_variables_hash({"name": "World", "age": 30})

        assert hash1 == hash2

    def test_variables_hash_order_independent(self):
        """Test that variables hash is independent of key order."""
        engine = TemplateEngine(self.template_dir)

        hash1 = engine._get_variables_hash({"a": 1, "b": 2, "c": 3})
        hash2 = engine._get_variables_hash({"c": 3, "a": 1, "b": 2})

        assert hash1 == hash2

    def test_cache_with_output_file(self):
        """Test that cache is updated even when rendering to output file."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        output_file = Path(self.temp_dir) / "output.txt"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"}, output=output_file)

        is_valid, reason = engine.get_cache_status(template_file, {"name": "World"})

        assert is_valid is True
        assert reason == "valid"

    def test_cache_timestamp_tracks_render(self):
        """Test that cache tracks when template was rendered."""
        import time

        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        before_render = time.monotonic()
        engine.render_file(template_file, {"name": "World"})
        after_render = time.monotonic()

        cached = engine._cache[template_file]
        assert before_render <= cached.rendered_at <= after_render

    def test_cache_statistics_tracking(self):
        """Test that cache statistics are properly tracked."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        stats_before = engine.get_cache_statistics()
        assert stats_before.hits == 0
        assert stats_before.misses == 0
        assert stats_before.renders == 0

        engine.render_file(template_file, {"name": "World"})

        stats_after_render = engine.get_cache_statistics()
        assert stats_after_render.renders == 1

        engine.render_file(template_file, {"name": "World"})

        stats_after_second_render = engine.get_cache_statistics()
        assert stats_after_second_render.hits == 1
        assert stats_after_second_render.misses == 1

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})
        engine.render_file(template_file, {"name": "World"})
        engine.render_file(template_file, {"name": "World"})

        stats = engine.get_cache_statistics()
        assert stats.hits == 2
        assert stats.misses == 1
        assert abs(stats.hit_rate - 2 / 3) < 0.01

    def test_cache_access_tracking(self):
        """Test that cache access counts are tracked."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})
        engine.render_file(template_file, {"name": "World"})

        cached = engine._cache[template_file]
        assert cached.access_count == 2

    def test_get_cache_info(self):
        """Test getting comprehensive cache information."""
        engine = TemplateEngine(self.template_dir)
        template_file1 = self.template_dir / "template1.j2"
        template_file2 = self.template_dir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file2, {"name": "World"})

        info = engine.get_cache_info()

        assert info["cache_size"] == 2
        assert len(info["entries"]) == 2
        assert "statistics" in info

    def test_most_accessed_templates(self):
        """Test getting most accessed templates."""
        engine = TemplateEngine(self.template_dir)
        template_file1 = self.template_dir / "template1.j2"
        template_file2 = self.template_dir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file2, {"name": "World"})

        most_accessed = engine.get_most_accessed_templates(limit=1)

        assert len(most_accessed) == 1
        assert most_accessed[0][0] == template_file1
        assert most_accessed[0][1] == 1

    def test_oldest_templates(self):
        """Test getting oldest rendered templates."""
        import time

        engine = TemplateEngine(self.template_dir)
        template_file1 = self.template_dir / "template1.j2"
        template_file2 = self.template_dir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        time.sleep(0.01)
        engine.render_file(template_file2, {"name": "World"})

        oldest = engine.get_oldest_templates(limit=1)

        assert len(oldest) == 1
        assert oldest[0][0] == template_file1

    def test_clear_statistics(self):
        """Test clearing cache statistics."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})
        engine.render_file(template_file, {"name": "World"})

        engine.clear_statistics()

        stats = engine.get_cache_statistics()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.renders == 0

    def test_invalidate_cache_by_pattern(self):
        """Test invalidating cache by glob pattern."""
        engine = TemplateEngine(self.template_dir)
        template_file1 = self.template_dir / "template1.j2"
        template_file2 = self.template_dir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file2, {"name": "World"})

        count = engine.invalidate_cache_by_pattern("template1.j2")

        assert count == 1
        assert len(engine._cache) == 1
        assert template_file2 in engine._cache
        assert template_file1 not in engine._cache

    def test_invalidate_cache_by_directory(self):
        """Test invalidating cache by directory."""
        engine = TemplateEngine(self.template_dir)
        subdir = self.template_dir / "subdir"
        subdir.mkdir()

        template_file1 = self.template_dir / "template1.j2"
        template_file2 = subdir / "template2.j2"
        template_file1.write_text("Hello {{ name }}!")
        template_file2.write_text("Goodbye {{ name }}!")

        engine.render_file(template_file1, {"name": "World"})
        engine.render_file(template_file2, {"name": "World"})

        count = engine.invalidate_cache_by_directory(self.template_dir)

        assert count == 2
        assert len(engine._cache) == 0

    def test_cache_statistics_to_dict(self):
        """Test cache statistics serialization to dictionary."""
        engine = TemplateEngine(self.template_dir)
        template_file = self.template_dir / "template.j2"
        template_file.write_text("Hello {{ name }}!")

        engine.render_file(template_file, {"name": "World"})
        engine.render_file(template_file, {"name": "World"})

        stats = engine.get_cache_statistics()
        stats_dict = stats.to_dict()

        assert "hits" in stats_dict
        assert "misses" in stats_dict
        assert "hit_rate" in stats_dict
        assert "miss_rate" in stats_dict
        assert stats_dict["hits"] == 1
        assert stats_dict["misses"] == 1
