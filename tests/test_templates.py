import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from quillion_cli.utils.templates import process_templates


class TestTemplate:
    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories for testing."""
        project_dir = tmp_path / "project"
        templates_dir = tmp_path / "templates"
        project_dir.mkdir()
        templates_dir.mkdir()
        return project_dir, templates_dir

    @pytest.fixture
    def sample_context(self):
        """Return sample context for template rendering."""
        return {
            "project_name": "test_project",
            "version": "1.0.0",
            "author": "Test Author"
        }

    def test_process_templates_basic(self, temp_dirs, sample_context):
        """Test basic template processing with a simple template."""
        project_dir, templates_dir = temp_dirs
        
        template_file = templates_dir / "test.txt.j2"
        template_file.write_text("Hello {{ project_name }}!")
        
        process_templates(str(project_dir), sample_context, templates_dir)
        
        expected_file = project_dir / "test.txt"
        assert expected_file.exists()
        assert expected_file.read_text() == "Hello test_project!"

    def test_process_templates_windows_paths(self, temp_dirs, sample_context):
        """Test that Windows-style paths are handled correctly."""
        project_dir, templates_dir = temp_dirs
        
        template_file = templates_dir / "windows" / "file.txt.j2"
        template_file.parent.mkdir()
        template_file.write_text("Windows test: {{ project_name }}")
        
        with patch.object(Path, 'relative_to') as mock_relative:
            mock_relative.return_value = Path("windows\\file.txt.j2")
            
            with patch.object(Path, 'with_suffix') as mock_suffix:
                mock_suffix.return_value = Path("windows/file.txt")
                
                process_templates(str(project_dir), sample_context, templates_dir)

    def test_process_templates_empty_context(self, temp_dirs):
        """Test template processing with empty context."""
        project_dir, templates_dir = temp_dirs
        
        template_file = templates_dir / "empty.txt.j2"
        template_file.write_text("Static content")
        
        process_templates(str(project_dir), {}, templates_dir)
        
        expected_file = project_dir / "empty.txt"
        assert expected_file.exists()
        assert expected_file.read_text() == "Static content"

    def test_process_templates_creates_parent_dirs(self, temp_dirs, sample_context):
        """Test that parent directories are created when they don't exist."""
        project_dir, templates_dir = temp_dirs
        
        deep_dir = templates_dir / "very" / "deep" / "nested" / "structure"
        deep_dir.mkdir(parents=True)
        template_file = deep_dir / "file.txt.j2"
        template_file.write_text("Deep nested: {{ project_name }}")
        
        target_parent = project_dir / "very" / "deep" / "nested" / "structure"
        assert not target_parent.exists()
        
        process_templates(str(project_dir), sample_context, templates_dir)
        
        expected_file = target_parent / "file.txt"
        assert expected_file.exists()
        assert expected_file.read_text() == "Deep nested: test_project"

    def test_process_templates_multiple_files(self, temp_dirs, sample_context):
        """Test processing multiple template files."""
        project_dir, templates_dir = temp_dirs
        
        templates = {
            "file1.txt.j2": "First: {{ project_name }}",
            "file2.txt.j2": "Second: {{ version }}",
            "subdir/file3.txt.j2": "Third: {{ author }}"
        }
        
        for template_path, content in templates.items():
            template_file = templates_dir / template_path
            template_file.parent.mkdir(parents=True, exist_ok=True)
            template_file.write_text(content)
        
        process_templates(str(project_dir), sample_context, templates_dir)
        
        assert (project_dir / "file1.txt").read_text() == "First: test_project"
        assert (project_dir / "file2.txt").read_text() == "Second: 1.0.0"
        assert (project_dir / "subdir" / "file3.txt").read_text() == "Third: Test Author"

    def test_process_templates_jinja2_syntax(self, temp_dirs, sample_context):
        """Test that Jinja2 syntax is properly rendered."""
        project_dir, templates_dir = temp_dirs
        
        template_content = """{% if version -%}
Project: {{ project_name }}
Version: {{ version }}
{% endif -%}
Author: {{ author }}"""
        
        template_file = templates_dir / "complex.py.j2"
        template_file.write_text(template_content)
        
        process_templates(str(project_dir), sample_context, templates_dir)
        
        expected_file = project_dir / "complex.py"
        expected_content = """Project: test_project
Version: 1.0.0
Author: Test Author"""
        assert expected_file.read_text() == expected_content

    def test_process_templates_jinja2_syntax_with_whitespace(self, temp_dirs, sample_context):
        """Test Jinja2 syntax with expected whitespace."""
        project_dir, templates_dir = temp_dirs
        
        template_content = """{% if version %}
Project: {{ project_name }}
Version: {{ version }}
{% endif %}
Author: {{ author }}
"""
        
        template_file = templates_dir / "complex.py.j2"
        template_file.write_text(template_content)
        
        process_templates(str(project_dir), sample_context, templates_dir)
        
        expected_file = project_dir / "complex.py"
        rendered_content = expected_file.read_text()
        assert "Project: test_project" in rendered_content
        assert "Version: 1.0.0" in rendered_content
        assert "Author: Test Author" in rendered_content

    @patch('quillion_cli.utils.templates.Environment')
    def test_process_templates_template_not_found(self, mock_env, temp_dirs, sample_context):
        """Test behavior when template is not found."""
        project_dir, templates_dir = temp_dirs
        
        mock_env_instance = Mock()
        mock_env.return_value = mock_env_instance
        mock_env_instance.get_template.side_effect = TemplateNotFound("test.txt.j2")
        
        template_file = templates_dir / "test.txt.j2"
        template_file.write_text("content")
        
        with pytest.raises(TemplateNotFound):
            process_templates(str(project_dir), sample_context, templates_dir)

    def test_process_templates_no_templates(self, temp_dirs, sample_context):
        """Test behavior when templates directory is empty."""
        project_dir, templates_dir = temp_dirs
        
        process_templates(str(project_dir), sample_context, templates_dir)
        
        assert not any(project_dir.iterdir())

    def test_process_templates_symlink_handling(self, temp_dirs, sample_context):
        """Test that symlinks are handled properly (should follow symlinks)."""
        project_dir, templates_dir = temp_dirs
        
        original_file = templates_dir / "original.txt.j2"
        original_file.write_text("Original: {{ project_name }}")
        
        try:
            symlink_file = templates_dir / "symlink.txt.j2"
            symlink_file.symlink_to(original_file)
            
            process_templates(str(project_dir), sample_context, templates_dir)
            
            assert (project_dir / "original.txt").exists()
            assert (project_dir / "symlink.txt").exists()
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

    def test_process_templates_special_characters(self, temp_dirs):
        """Test template processing with special characters in context."""
        project_dir, templates_dir = temp_dirs
        
        context = {
            "name": "Test & Name",
            "path": "some/path/with/slashes",
            "html": "<div>Test</div>"
        }
        
        template_file = templates_dir / "special.txt.j2"
        template_file.write_text("Name: {{ name }}, Path: {{ path }}, HTML: {{ html }}")
        
        process_templates(str(project_dir), context, templates_dir)
        
        expected_file = project_dir / "special.txt"
        assert expected_file.exists()
        assert expected_file.read_text() == "Name: Test & Name, Path: some/path/with/slashes, HTML: <div>Test</div>"

    def test_process_templates_preserves_file_extension(self, temp_dirs, sample_context):
        """Test that file extensions are preserved correctly when removing .j2 suffix."""
        project_dir, templates_dir = temp_dirs
        
        test_cases = [
            "script.py.j2",
            "config.yaml.j2", 
            "README.md.j2",
            "file.no.extension.j2"
        ]
        
        for template_name in test_cases:
            template_file = templates_dir / template_name
            template_file.write_text("Content for {{ project_name }}")
            
        process_templates(str(project_dir), sample_context, templates_dir)
        
        assert (project_dir / "script.py").exists()
        assert (project_dir / "config.yaml").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "file.no.extension").exists()