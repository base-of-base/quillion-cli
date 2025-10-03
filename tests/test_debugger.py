import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call
import sys

from quillion_cli.debug.debugger import Debugger, debugger, initial_config
from quillion_cli.config.models import DebugConfig


class TestDebugger:
    @pytest.fixture
    def debug_config(self):
        """Create a debug configuration for testing."""
        return DebugConfig(quiet=False, no_color=False, no_figlet=False)

    @pytest.fixture
    def debug_config_quiet(self):
        """Create a quiet debug configuration."""
        return DebugConfig(quiet=True, no_color=False, no_figlet=False)

    @pytest.fixture
    def debug_config_no_color(self):
        """Create a no-color debug configuration."""
        return DebugConfig(quiet=False, no_color=True, no_figlet=False)

    @pytest.fixture
    def debug_config_no_figlet(self):
        """Create a no-figlet debug configuration."""
        return DebugConfig(quiet=False, no_color=False, no_figlet=True)

    @pytest.fixture
    def mock_console(self):
        """Mock the rich Console."""
        with patch("quillion_cli.debug.debugger.Console") as mock_console_class:
            mock_console = Mock()
            mock_console_class.return_value = mock_console
            yield mock_console

    def test_initial_config_from_environment(self):
        """Test that initial_config reads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "QUILLION_QUIET": "1",
                "QUILLION_NO_COLOR": "1",
                "QUILLION_NO_FIGLET": "1",
            },
        ):
            import importlib
            import quillion_cli.debug.debugger

            importlib.reload(quillion_cli.debug.debugger)

            config = quillion_cli.debug.debugger.initial_config
            assert config.quiet is True
            assert config.no_color is True
            assert config.no_figlet is True

    def test_initial_config_defaults(self):
        """Test that initial_config uses defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import quillion_cli.debug.debugger

            importlib.reload(quillion_cli.debug.debugger)

            config = quillion_cli.debug.debugger.initial_config
            assert config.quiet is False
            assert config.no_color is False
            assert config.no_figlet is False

    def test_debugger_initialization(self, debug_config, mock_console):
        """Test Debugger initialization."""
        debugger = Debugger(debug_config)

        assert debugger.config == debug_config
        assert debugger.console == mock_console

    def test_should_log_when_not_quiet(self, debug_config, mock_console):
        """Test _should_log returns True when not quiet."""
        debugger = Debugger(debug_config)
        assert debugger._should_log() is True

    def test_should_log_when_quiet(self, debug_config_quiet, mock_console):
        """Test _should_log returns False when quiet."""
        debugger = Debugger(debug_config_quiet)
        assert debugger._should_log() is False

    def test_format_message_with_color(self, debug_config, mock_console):
        """Test _format_message with color enabled."""
        debugger = Debugger(debug_config)

        with patch("quillion_cli.debug.debugger.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "12:00:00"

            result = debugger._format_message("✓", "Test message")

            expected = "[bold blue]12:00:00[/] [dim]│[/] ✓ Test message"
            assert result == expected

    def test_format_message_no_color(self, debug_config_no_color, mock_console):
        """Test _format_message with color disabled."""
        debugger = Debugger(debug_config_no_color)

        with patch("quillion_cli.debug.debugger.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "12:00:00"

            result = debugger._format_message("✓", "Test message")

            expected = "12:00:00 │ ✓ Test message"
            assert result == expected

    def test_info_logs_when_not_quiet(self, debug_config, mock_console):
        """Test info method logs when not quiet."""
        debugger = Debugger(debug_config)

        with patch.object(debugger, "_format_message") as mock_format:
            mock_format.return_value = "formatted_message"

            debugger.info("Test info message")

            mock_format.assert_called_once_with("", "Test info message")
            mock_console.print.assert_called_once_with("formatted_message")

    def test_info_skips_when_quiet(self, debug_config_quiet, mock_console):
        """Test info method skips logging when quiet."""
        debugger = Debugger(debug_config_quiet)

        debugger.info("Test info message")

        mock_console.print.assert_not_called()

    def test_success_logs_when_not_quiet(self, debug_config, mock_console):
        """Test success method logs when not quiet."""
        debugger = Debugger(debug_config)

        with patch.object(debugger, "_format_message") as mock_format:
            mock_format.return_value = "formatted_message"

            debugger.success("Test success message")

            symbol = "[green]✓[/]"
            mock_format.assert_called_once_with(symbol, "Test success message")
            mock_console.print.assert_called_once_with("formatted_message")

    def test_success_no_color(self, debug_config_no_color, mock_console):
        """Test success method with no color."""
        debugger = Debugger(debug_config_no_color)

        with patch.object(debugger, "_format_message") as mock_format:
            mock_format.return_value = "formatted_message"

            debugger.success("Test success message")

            symbol = "✓"
            mock_format.assert_called_once_with(symbol, "Test success message")

    def test_warning_logs_when_not_quiet(self, debug_config, mock_console):
        """Test warning method logs when not quiet."""
        debugger = Debugger(debug_config)

        with patch.object(debugger, "_format_message") as mock_format:
            mock_format.return_value = "formatted_message"

            debugger.warning("Test warning message")

            symbol = "[yellow]⚠[/]"
            mock_format.assert_called_once_with(symbol, "Test warning message")
            mock_console.print.assert_called_once_with("formatted_message")

    def test_warning_no_color(self, debug_config_no_color, mock_console):
        """Test warning method with no color."""
        debugger = Debugger(debug_config_no_color)

        with patch.object(debugger, "_format_message") as mock_format:
            mock_format.return_value = "formatted_message"

            debugger.warning("Test warning message")

            symbol = "⚠"
            mock_format.assert_called_once_with(symbol, "Test warning message")

    def test_error_logs_when_not_quiet(self, debug_config, mock_console):
        """Test error method logs when not quiet."""
        debugger = Debugger(debug_config)

        with patch.object(debugger, "_format_message") as mock_format:
            mock_format.return_value = "formatted_message"

            debugger.error("Test error message")

            symbol = "[red][/]"
            mock_format.assert_called_once_with(symbol, "Test error message")
            mock_console.print.assert_called_once_with("formatted_message")

    def test_error_skips_when_quiet(self, debug_config_quiet, mock_console):
        """Test error method skips logging when quiet."""
        debugger = Debugger(debug_config_quiet)

        debugger.error("Test error message")

        mock_console.print.assert_not_called()

    def test_version_logs_when_not_quiet(self, debug_config, mock_console):
        """Test version method logs when not quiet."""
        debugger = Debugger(debug_config)

        with patch("quillion_cli.debug.debugger.__version__", "1.2.3"):
            debugger.version()

            expected = "[bold green]Quillion CLI[/] v[cyan]1.2.3[/]"
            mock_console.print.assert_called_once_with(expected)

    def test_version_no_color(self, debug_config_no_color, mock_console):
        """Test version method with no color."""
        debugger = Debugger(debug_config_no_color)

        with patch("quillion_cli.debug.debugger.__version__", "1.2.3"):
            debugger.version()

            expected = "Quillion CLI v1.2.3"
            mock_console.print.assert_called_once_with(expected)

    def test_version_skips_when_quiet(self, debug_config_quiet, mock_console):
        """Test version method skips when quiet."""
        debugger = Debugger(debug_config_quiet)

        debugger.version()

        mock_console.print.assert_not_called()

    def test_server_start_no_color(self, debug_config_no_color, mock_console):
        """Test server_start method with no color."""
        debugger = Debugger(debug_config_no_color)

        with patch("quillion_cli.debug.debugger.os.get_terminal_size") as mock_terminal:
            mock_terminal.return_value.columns = 80

            debugger.server_start("localhost", 8000, 8080, https=False)

            calls = mock_console.print.call_args_list
            assert any("Server running!" in str(call) for call in calls)
            assert any("ws://localhost:8000" in str(call) for call in calls)
            assert any("http://localhost:8080" in str(call) for call in calls)

    def test_server_start_skips_when_quiet(self, debug_config_quiet, mock_console):
        """Test server_start method skips when quiet."""
        debugger = Debugger(debug_config_quiet)

        debugger.server_start("localhost", 8000, 8080)

        mock_console.print.assert_not_called()

    def test_http_server_start_with_color(self, debug_config, mock_console):
        """Test http_server_start method with color enabled."""
        debugger = Debugger(debug_config)

        debugger.http_server_start("localhost", 8080, https=False)

        calls = mock_console.print.call_args_list
        assert len(calls) == 2
        assert "HTTP server started on localhost:8080" in str(calls[0])
        assert "Serving static files from packages directory" in str(calls[1])

    def test_http_server_start_https(self, debug_config, mock_console):
        """Test http_server_start method with HTTPS."""
        debugger = Debugger(debug_config)

        debugger.http_server_start("localhost", 8080, https=True)

        calls = mock_console.print.call_args_list
        assert "HTTPS server started on localhost:8080" in str(calls[0])

    def test_http_server_start_no_color(self, debug_config_no_color, mock_console):
        """Test http_server_start method with no color."""
        debugger = Debugger(debug_config_no_color)

        debugger.http_server_start("localhost", 8080, https=False)

        calls = mock_console.print.call_args_list
        expected_call = (
            "[green]✓[/] [bold]HTTP server[/] started on [cyan]localhost:8080[/]"
        )
        assert expected_call in str(calls[0])

    def test_http_server_start_skips_when_quiet(self, debug_config_quiet, mock_console):
        """Test http_server_start method skips when quiet."""
        debugger = Debugger(debug_config_quiet)

        debugger.http_server_start("localhost", 8080)

        mock_console.print.assert_not_called()

    def test_banner_shows_when_not_quiet_and_figlet_enabled(
        self, debug_config, mock_console
    ):
        """Test banner method shows when conditions are met."""
        debugger = Debugger(debug_config)

        with patch("quillion_cli.debug.debugger.pyfiglet") as mock_pyfiglet:
            mock_pyfiglet.figlet_format.return_value = "FIGLET_TEXT"

            debugger.banner()

            mock_pyfiglet.figlet_format.assert_called_once_with("Q", font="slant")
            assert mock_console.print.call_count == 4

    def test_banner_skips_when_quiet(self, debug_config_quiet, mock_console):
        """Test banner method skips when quiet."""
        debugger = Debugger(debug_config_quiet)

        debugger.banner()

        mock_console.print.assert_not_called()

    def test_banner_skips_when_no_figlet(self, debug_config_no_figlet, mock_console):
        """Test banner method skips when no_figlet is enabled."""
        debugger = Debugger(debug_config_no_figlet)

        debugger.banner()

        mock_console.print.assert_not_called()

    def test_banner_handles_pyfiglet_error(self, debug_config, mock_console):
        """Test banner method handles pyfiglet errors gracefully."""
        debugger = Debugger(debug_config)

        with patch("quillion_cli.debug.debugger.pyfiglet") as mock_pyfiglet:
            mock_pyfiglet.figlet_format.side_effect = Exception("Figlet error")

            debugger.banner()

            mock_console.print.assert_called()

    def test_all_methods_use_should_log(self, debug_config_quiet, mock_console):
        """Test that all public methods respect the quiet setting."""
        debugger = Debugger(debug_config_quiet)

        debugger.info("test")
        debugger.success("test")
        debugger.warning("test")
        debugger.error("test")
        debugger.version()
        debugger.server_start("localhost", 8000, 8080)
        debugger.http_server_start("localhost", 8080)
        debugger.banner()

        mock_console.print.assert_not_called()

    def test_message_formatting_edge_cases(self, debug_config, mock_console):
        """Test message formatting with edge cases."""
        debugger = Debugger(debug_config)

        with patch.object(debugger, "_format_message") as mock_format:
            debugger.info("")
            mock_format.assert_called_once_with("", "")

        with patch.object(debugger, "_format_message") as mock_format:
            debugger.info("Message with \n newline and \t tab")
            mock_format.assert_called_once_with(
                "", "Message with \n newline and \t tab"
            )

    def test_terminal_size_handling(self, debug_config, mock_console):
        """Test handling of terminal size in server_start."""
        debugger = Debugger(debug_config)

        with patch("quillion_cli.debug.debugger.os.get_terminal_size") as mock_terminal:
            mock_terminal.return_value.columns = 40

            debugger.server_start("localhost", 8000, 8080)

            assert mock_console.print.called

    def test_multiple_instances_independent(self, mock_console):
        """Test that multiple Debugger instances are independent."""
        config1 = DebugConfig(quiet=True, no_color=False, no_figlet=False)
        config2 = DebugConfig(quiet=False, no_color=True, no_figlet=False)

        debugger1 = Debugger(config1)
        debugger2 = Debugger(config2)

        assert debugger1._should_log() is False
        assert debugger2._should_log() is True

        debugger1.info("test1")
        debugger2.info("test2")

        assert mock_console.print.call_count == 1


class TestDebuggerSingleton:
    """Tests for the global debugger instance."""

    def test_global_debugger_has_config(self):
        """Test that the global debugger has a config."""
        from quillion_cli.debug.debugger import debugger, initial_config

        assert debugger.config == initial_config


class TestDebuggerOutput:
    """Tests that verify the actual output formatting."""

    def test_actual_format_message_with_timestamp(self):
        """Test that _format_message includes actual timestamp."""
        debugger = Debugger(DebugConfig(quiet=False, no_color=True, no_figlet=False))

        result = debugger._format_message("✓", "Test message")

        import re

        timestamp_pattern = r"\d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, result)
        assert "│ ✓ Test message" in result

    def test_actual_console_output(self):
        """Test actual console output with a real console."""
        from rich.console import Console
        from io import StringIO

        debugger = Debugger(DebugConfig(quiet=False, no_color=True, no_figlet=False))

        output = StringIO()
        debugger.console = Console(file=output, color_system=None)

        debugger.info("Test message")

        output_str = output.getvalue()
        assert "Test message" in output_str
