import pytest
import typer
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import typing as t


class TestNewCommand:

    @pytest.fixture
    def mock_debugger(self):
        with patch("quillion_cli.commands.new.debugger") as mock_debugger:
            yield mock_debugger

    @pytest.fixture
    def mock_process_templates(self):
        with patch("quillion_cli.commands.new.process_templates") as mock_process:
            yield mock_process

    def _setup_path_mocks(
        self,
        MockPath,
        test_name,
        mock_templates_dir,
        mock_config_path,
        create_dir_exists=False,
    ):

        mock_project_dir = MagicMock()
        mock_project_dir.mkdir.return_value = None
        mock_project_dir.exists.return_value = create_dir_exists
        mock_project_dir.__str__ = lambda x: f"/mock/path/{test_name}"
        mock_project_dir.__truediv__.return_value = mock_config_path

        mock_path_name = Mock()
        mock_path_name.resolve.return_value = mock_project_dir

        mock_file_path = Mock()
        mock_file_path.parent = Mock()
        mock_file_path.parent.parent = Mock()
        mock_file_path.parent.parent.__truediv__ = Mock(return_value=mock_templates_dir)

        def mock_path_side_effect(arg):
            if arg == test_name:
                return mock_path_name
            return mock_file_path

        MockPath.side_effect = mock_path_side_effect

        return mock_project_dir

    def test_new_command_success(self, mock_debugger, mock_process_templates):
        """Test successful project creation"""
        from quillion_cli.commands.new import new_command

        test_name = "test_project"
        test_port = 1337
        test_host = "127.0.0.1"
        test_http_port = 8000

        with patch("quillion_cli.commands.new.Path") as MockPath:
            mock_config_path = Mock()
            mock_config_path.exists.return_value = False

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = True

            mock_project_dir = self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            new_command(
                name=test_name,
                port=test_port,
                host=test_host,
                http_port=test_http_port,
                non_interactive=True,
            )

            mock_project_dir.mkdir.assert_called_once_with(exist_ok=True)

            mock_process_templates.assert_called_once()

            call_args = mock_process_templates.call_args[0]
            context_arg = call_args[1]
            templates_dir_arg = call_args[2]

            assert call_args[0] == str(mock_project_dir)
            assert context_arg["project_name"] == test_name
            assert context_arg["port"] == test_port
            assert context_arg["host"] == test_host
            assert context_arg["http_port"] == test_http_port
            assert templates_dir_arg == mock_templates_dir

            mock_debugger.banner.assert_called_once()
            mock_debugger.success.assert_called_once()
            mock_debugger.info.assert_called_once()

    def test_new_command_no_name(self, mock_debugger):
        """Test project creation without name"""
        from quillion_cli.commands.new import new_command

        with patch("quillion_cli.commands.new.typer.Exit") as MockExit:
            MockExit.side_effect = Exception("Exit called")

            try:
                new_command(name=None)
                assert False, "Expected typer.Exit to be raised"
            except Exception as e:
                if str(e) == "Exit called":
                    mock_debugger.error.assert_called_once_with(
                        "Project name is required"
                    )
                else:
                    raise

    def test_new_command_existing_config_no_overwrite(
        self, mock_debugger, mock_process_templates
    ):
        """Test existing config with user declining overwrite"""
        from quillion_cli.commands.new import new_command

        test_name = "existing_project"

        with patch("quillion_cli.commands.new.Path") as MockPath, patch(
            "quillion_cli.commands.new.typer.confirm", return_value=False
        ) as mock_confirm:

            mock_config_path = Mock()
            mock_config_path.exists.return_value = True

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = True

            self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            new_command(name=test_name, non_interactive=False)

            mock_confirm.assert_called_once_with("Overwrite existing config?")

            mock_process_templates.assert_not_called()
            mock_debugger.warning.assert_called_once_with(
                "quillion.toml already exists in this directory"
            )

    def test_new_command_existing_config_force_overwrite(
        self, mock_debugger, mock_process_templates
    ):
        """Test existing config with non-interactive mode (auto-overwrite)"""
        from quillion_cli.commands.new import new_command

        test_name = "existing_project"

        with patch("quillion_cli.commands.new.Path") as MockPath:

            mock_config_path = Mock()
            mock_config_path.exists.return_value = True

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = True

            self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            new_command(name=test_name, non_interactive=True)

            mock_process_templates.assert_called_once()
            mock_debugger.warning.assert_called_once_with(
                "quillion.toml already exists in this directory"
            )

    def test_new_command_templates_not_found(self, mock_debugger):
        """Test when templates directory doesn't exist"""
        from quillion_cli.commands.new import new_command

        test_name = "test_project"

        with patch("quillion_cli.commands.new.Path") as MockPath:

            mock_config_path = Mock()
            mock_config_path.exists.return_value = False

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = False

            self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            with patch("quillion_cli.commands.new.typer.Exit") as MockExit:
                MockExit.side_effect = Exception("Exit called")

                try:
                    new_command(name=test_name, non_interactive=True)
                    assert False, "Expected typer.Exit to be raised"
                except Exception as e:
                    if str(e) == "Exit called":
                        mock_debugger.error.assert_called_once()
                        error_call_args = mock_debugger.error.call_args[0][0]
                        assert "Templates directory not found" in error_call_args
                    else:
                        raise

    def test_new_command_context_generation(
        self, mock_debugger, mock_process_templates
    ):
        """Test context generation with different parameters"""
        from quillion_cli.commands.new import new_command

        test_name = "my_project"
        test_port = 3000
        test_host = "0.0.0.0"
        test_http_port = 9000

        with patch("quillion_cli.commands.new.Path") as MockPath:

            mock_config_path = Mock()
            mock_config_path.exists.return_value = False

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = True

            self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            new_command(
                name=test_name,
                port=test_port,
                host=test_host,
                http_port=test_http_port,
                non_interactive=True,
            )

            call_args = mock_process_templates.call_args[0]
            context = call_args[1]

            assert context["project_name"] == test_name
            assert context["port"] == test_port
            assert context["host"] == test_host
            assert context["http_port"] == test_http_port
            assert context["websocket_address"] == f"ws://{test_host}:{test_port}"
            assert context["app_name"] == "My Project"

    def test_new_command_default_values(self, mock_debugger, mock_process_templates):
        """Test project creation with default values"""
        from quillion_cli.commands.new import new_command

        test_name = "default_project"

        with patch("quillion_cli.commands.new.Path") as MockPath:

            mock_config_path = Mock()
            mock_config_path.exists.return_value = False

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = True

            self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            new_command(
                name=test_name,
                port=1337,
                host="127.0.0.1",
                http_port=8000,
                non_interactive=True,
            )

            call_args = mock_process_templates.call_args[0]
            context = call_args[1]

            assert context["port"] == 1337
            assert context["host"] == "127.0.0.1"
            assert context["http_port"] == 8000

    def test_new_command_project_dir_creation(
        self, mock_debugger, mock_process_templates
    ):
        """Test project directory creation"""
        from quillion_cli.commands.new import new_command

        test_name = "test_dir"

        with patch("quillion_cli.commands.new.Path") as MockPath:

            mock_config_path = Mock()
            mock_config_path.exists.return_value = False

            mock_templates_dir = Mock()
            mock_templates_dir.exists.return_value = True

            mock_project_dir = self._setup_path_mocks(
                MockPath,
                test_name,
                mock_templates_dir,
                mock_config_path,
                create_dir_exists=False,
            )

            new_command(name=test_name, non_interactive=True)

            mock_project_dir.mkdir.assert_called_once_with(exist_ok=True)

            mock_process_templates.assert_called_once()
            call_args = mock_process_templates.call_args[0]
            assert call_args[0] == str(mock_project_dir)
