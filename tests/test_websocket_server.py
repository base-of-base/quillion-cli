import pytest
import tempfile
import subprocess
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import contextlib

sys.path.insert(0, str(Path(__file__).parent.parent))

from quillion_cli.server.websocket_server import (
    run_server,
    restart_server,
    shutdown_server,
)


class TestServerProcess:
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            yield project_dir

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()

        config.server.host = "127.0.0.1"
        config.server.port = 8000
        config.server.entry_point = "main.py"

        config.assets.host = "localhost"
        config.assets.port = 8080
        config.assets.path = "/assets"

        config.debugger.quiet = False
        config.debugger.no_color = False
        config.debugger.no_figlet = False

        return config

    @pytest.fixture
    def mock_debugger(self):
        """Mock the debugger module."""
        with patch("quillion_cli.server.websocket_server.debugger") as mock_debugger:
            yield mock_debugger

    def test_run_server_entry_point_not_found(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server startup when entry point doesn't exist."""

        result = run_server(mock_config, str(temp_project_dir))

        assert result is None
        expected_entry_point = temp_project_dir / "main.py"
        mock_debugger.error.assert_called_once_with(
            f"Entry point not found: {expected_entry_point}"
        )

    def test_run_server_with_debugger_flags(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server startup with debugger flags enabled."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_config.debugger.quiet = True
        mock_config.debugger.no_color = True
        mock_config.debugger.no_figlet = True

        mock_process = Mock()
        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_process

            result = run_server(mock_config, str(temp_project_dir))

            call_args = mock_popen.call_args
            env = call_args[1]["env"]
            assert env["QUILLION_QUIET"] == "1"
            assert env["QUILLION_NO_COLOR"] == "1"
            assert env["QUILLION_NO_FIGLET"] == "1"

            assert result == mock_process

    def test_run_server_popen_exception(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server startup when Popen raises an exception."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.side_effect = Exception("Permission denied")

            result = run_server(mock_config, str(temp_project_dir))

            assert result is None
            mock_debugger.error.assert_called_once_with(
                "Cannot run server: Permission denied"
            )

    def test_run_server_environment_preserved(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test that existing environment variables are preserved."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        original_env = os.environ.copy()
        os.environ["CUSTOM_VAR"] = "custom_value"
        os.environ["ANOTHER_VAR"] = "another_value"

        try:
            mock_process = Mock()
            with patch(
                "quillion_cli.server.websocket_server.subprocess.Popen"
            ) as mock_popen:
                mock_popen.return_value = mock_process

                result = run_server(mock_config, str(temp_project_dir))

                call_args = mock_popen.call_args
                env = call_args[1]["env"]
                assert env["CUSTOM_VAR"] == "custom_value"
                assert env["ANOTHER_VAR"] == "another_value"
                assert env["PATH"] == os.environ["PATH"]

        finally:
            if "CUSTOM_VAR" in os.environ:
                del os.environ["CUSTOM_VAR"]
            if "ANOTHER_VAR" in os.environ:
                del os.environ["ANOTHER_VAR"]

    def test_restart_server_with_existing_process(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server restart with an existing process."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_old_process = Mock()
        mock_new_process = Mock()

        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_new_process

            result = restart_server(
                mock_config, str(temp_project_dir), mock_old_process
            )

            mock_old_process.terminate.assert_called_once()
            mock_old_process.wait.assert_called_once_with(timeout=5)

            mock_popen.assert_called_once()

            assert result == mock_new_process

    def test_restart_server_terminate_timeout(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server restart when terminate times out but kill succeeds."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_old_process = Mock()
        mock_old_process.terminate.side_effect = Exception("Terminate failed")
        mock_old_process.wait.side_effect = subprocess.TimeoutExpired(
            cmd="test", timeout=5
        )

        mock_new_process = Mock()

        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_new_process

            result = restart_server(
                mock_config, str(temp_project_dir), mock_old_process
            )

            mock_old_process.kill.assert_called_once()

            assert result == mock_new_process

    def test_restart_server_no_existing_process(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server restart when no existing process is provided."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_new_process = Mock()

        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_new_process

            result = restart_server(mock_config, str(temp_project_dir), None)

            mock_popen.assert_called_once()
            assert result == mock_new_process

    def test_restart_server_run_server_fails(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server restart when run_server returns None."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_old_process = Mock()

        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = None

            result = restart_server(
                mock_config, str(temp_project_dir), mock_old_process
            )

            assert result is None

            mock_old_process.terminate.assert_called_once()

    def test_shutdown_server_terminate_fails(self):
        """Test server shutdown when terminate fails."""
        mock_process = Mock()
        mock_process.terminate.side_effect = Exception("Terminate failed")

        shutdown_server(mock_process)

        mock_process.kill.assert_called_once()

    def test_shutdown_server_wait_timeout(self):
        """Test server shutdown when wait times out."""
        mock_process = Mock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)

        shutdown_server(mock_process)

        mock_process.kill.assert_called_once()

    def test_shutdown_server_none_process(self):
        """Test server shutdown with None process."""
        shutdown_server(None)

    def test_shutdown_server_multiple_failures(self):
        """Test server shutdown when both terminate and kill fail."""
        mock_process = Mock()
        mock_process.terminate.side_effect = Exception("Terminate failed")
        mock_process.kill.side_effect = Exception("Kill failed")

        shutdown_server(mock_process)

    def test_run_server_custom_entry_point(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server startup with custom entry point."""
        custom_entry = temp_project_dir / "custom_main.py"
        custom_entry.write_text("print('Custom Entry')")

        mock_config.server.entry_point = "custom_main.py"

        mock_process = Mock()
        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_process

            result = run_server(mock_config, str(temp_project_dir))

            call_args = mock_popen.call_args
            expected_cmd = [sys.executable, str(custom_entry)]
            assert call_args[0][0] == expected_cmd

            assert result == mock_process

    def test_run_server_entry_point_in_subdirectory(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test server startup with entry point in subdirectory."""
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        entry_point = src_dir / "app.py"
        entry_point.write_text("print('App')")

        mock_config.server.entry_point = "src/app.py"

        mock_process = Mock()
        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_process

            result = run_server(mock_config, str(temp_project_dir))

            call_args = mock_popen.call_args
            expected_cmd = [sys.executable, str(entry_point)]
            assert call_args[0][0] == expected_cmd

            assert result == mock_process

    def test_environment_variable_types(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test that environment variables have correct types."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_config.server.port = 9000
        mock_config.assets.port = 9090

        mock_process = Mock()
        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_process

            result = run_server(mock_config, str(temp_project_dir))

            call_args = mock_popen.call_args
            env = call_args[1]["env"]
            assert env["QUILLION_PORT"] == "9000"
            assert env["QUILLION_ASSET_PORT"] == "9090"
            assert isinstance(env["QUILLION_PORT"], str)
            assert isinstance(env["QUILLION_ASSET_PORT"], str)

    def test_restart_server_preserves_working_directory(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test that restart_server preserves the working directory."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_old_process = Mock()
        mock_new_process = Mock()

        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_new_process

            result = restart_server(
                mock_config, str(temp_project_dir), mock_old_process
            )

            call_args = mock_popen.call_args
            assert call_args[1]["cwd"] == str(temp_project_dir)

    @patch.dict(os.environ, {"QUILLION_EXISTING_VAR": "existing_value"}, clear=False)
    def test_run_server_does_not_clear_existing_env(
        self, temp_project_dir, mock_config, mock_debugger
    ):
        """Test that run_server doesn't clear existing environment variables."""
        entry_point = temp_project_dir / "main.py"
        entry_point.write_text("print('Hello World')")

        mock_process = Mock()
        with patch(
            "quillion_cli.server.websocket_server.subprocess.Popen"
        ) as mock_popen:
            mock_popen.return_value = mock_process

            result = run_server(mock_config, str(temp_project_dir))

            call_args = mock_popen.call_args
            env = call_args[1]["env"]
            assert env["QUILLION_EXISTING_VAR"] == "existing_value"
