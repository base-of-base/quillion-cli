import pytest
import typer
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import typing as t

class TestRunCommand:

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.server.port = 8000
        config.server.host = "localhost"
        config.http_server.port = 8080
        config.http_server.enabled = True
        config.assets.port = 3000
        config.assets.host = "localhost"
        config.assets.path = "/assets"
        return config

    @pytest.fixture
    def mock_debugger(self):
        with patch('quillion_cli.commands.run.debugger.banner') as mock_banner, \
             patch('quillion_cli.commands.run.debugger.error') as mock_error, \
             patch('quillion_cli.commands.run.debugger.info') as mock_info, \
             patch('quillion_cli.commands.run.debugger.server_start') as mock_server_start:
            yield {
                'banner': mock_banner,
                'error': mock_error,
                'info': mock_info,
                'server_start': mock_server_start
            }

    @pytest.fixture
    def mock_servers(self):
        with patch('quillion_cli.commands.run.run_server') as mock_run_server, \
             patch('quillion_cli.commands.run.start_http_server') as mock_http_server, \
             patch('quillion_cli.commands.run.restart_server') as mock_restart_server, \
             patch('quillion_cli.commands.run.setup_file_watchers') as mock_watchers, \
             patch('quillion_cli.commands.run.shutdown_server') as mock_shutdown_server, \
             patch('quillion_cli.commands.run.shutdown_watchers') as mock_shutdown_watchers:
            
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.wait.side_effect = KeyboardInterrupt()
            mock_run_server.return_value = mock_process
            
            mock_httpd = Mock()
            mock_http_thread = Mock()
            mock_http_server.return_value = (mock_httpd, mock_http_thread)
            
            mock_observers = [Mock(), Mock()]
            mock_watchers.return_value = mock_observers
            
            yield {
                'run_server': mock_run_server,
                'http_server': mock_http_server,
                'restart_server': mock_restart_server,
                'watchers': mock_watchers,
                'shutdown_server': mock_shutdown_server,
                'shutdown_watchers': mock_shutdown_watchers,
                'process': mock_process,
                'httpd': mock_httpd,
                'observers': mock_observers
            }

    def test_run_command_with_project(self, mock_config, mock_debugger, mock_servers):
        with patch('quillion_cli.commands.run.load_config', return_value=mock_config), \
             patch('quillion_cli.commands.run.start_development_server') as mock_start_dev:
            
            from quillion_cli.commands.run import run_command
            test_dir = "/test/project"
            with patch.object(Path, 'exists', return_value=True):
                run_command(name=test_dir)
                
                mock_start_dev.assert_called_once()

    def test_run_command_config_overrides(self, mock_config, mock_debugger, mock_servers):
        with patch('quillion_cli.commands.run.load_config', return_value=mock_config), \
             patch('quillion_cli.commands.run.start_development_server') as mock_start_dev:
            
            from quillion_cli.commands.run import run_command
            with patch.object(Path, 'exists', return_value=True):
                run_command(
                    name="test_project",
                    hot_reload=False,
                    port=9000,
                    host="0.0.0.0",
                    http_port=9090,
                    no_http=True,
                    assets_port=4000,
                    assets_host="127.0.0.1",
                    assets_path="/static"
                )
            
            assert mock_config.server.port == 9000
            assert mock_config.server.host == "0.0.0.0"
            assert mock_config.http_server.port == 9090
            assert mock_config.http_server.enabled == False
            assert mock_config.assets.port == 4000
            assert mock_config.assets.host == "127.0.0.1"
            assert mock_config.assets.path == "/static"
            
            mock_start_dev.assert_called_once()

    def test_start_development_server_no_hot_reload(self, mock_config, mock_debugger, mock_servers):
        with patch('time.sleep', side_effect=KeyboardInterrupt()):
            from quillion_cli.commands.run import start_development_server
            start_development_server(mock_config, "/test/project", hot_reload=False)
            
            mock_servers['run_server'].assert_called_once_with(mock_config, "/test/project")
            mock_servers['process'].wait.assert_called_once()

    def test_start_development_server_with_hot_reload(self, mock_config, mock_debugger, mock_servers):
        mock_servers['process'].poll.return_value = None
        with patch('time.sleep', side_effect=KeyboardInterrupt()):
            from quillion_cli.commands.run import start_development_server
            start_development_server(mock_config, "/test/project", hot_reload=True)
            
            mock_servers['run_server'].assert_called_once_with(mock_config, "/test/project")
            mock_servers['watchers'].assert_called_once()
            mock_servers['shutdown_server'].assert_called_once_with(mock_servers['process'])
            mock_servers['shutdown_watchers'].assert_called_once_with(mock_servers['observers'])

    def test_start_development_server_process_dies(self, mock_config, mock_debugger, mock_servers):
        mock_servers['process'].poll.side_effect = [1, KeyboardInterrupt()]
        mock_servers['restart_server'].return_value = Mock()
        
        with patch('time.sleep', side_effect=[None, KeyboardInterrupt()]):
            from quillion_cli.commands.run import start_development_server
            start_development_server(mock_config, "/test/project", hot_reload=True)
            
            mock_servers['restart_server'].assert_called_once_with(mock_config, "/test/project", mock_servers['process'])

    def test_shutdown_servers(self, mock_servers):
        from quillion_cli.commands.run import shutdown_servers
        process = Mock()
        httpd = Mock()
        observers = [Mock(), Mock()]
        
        shutdown_servers(process, httpd, observers)
        
        mock_servers['shutdown_server'].assert_called_once_with(process)
        httpd.shutdown.assert_called_once()
        mock_servers['shutdown_watchers'].assert_called_once_with(observers)

    def test_shutdown_servers_none_httpd(self, mock_servers):
        from quillion_cli.commands.run import shutdown_servers
        process = Mock()
        observers = [Mock(), Mock()]
        
        shutdown_servers(process, None, observers)
        
        mock_servers['shutdown_server'].assert_called_once_with(process)
        mock_servers['shutdown_watchers'].assert_called_once_with(observers)

    def test_start_development_server_debugger_calls(self, mock_config, mock_debugger, mock_servers):
        with patch('time.sleep', side_effect=KeyboardInterrupt()):
            from quillion_cli.commands.run import start_development_server
            start_development_server(mock_config, "/test/project", hot_reload=True)
            
            mock_debugger['server_start'].assert_called_once_with(
                "localhost",
                8000,
                8080
            )

    def test_run_server_returns_none(self, mock_config, mock_debugger, mock_servers):
        mock_servers['run_server'].return_value = None
        
        from quillion_cli.commands.run import start_development_server
        start_development_server(mock_config, "/test/project", hot_reload=True)
        
        mock_servers['http_server'].assert_not_called()
        mock_debugger['server_start'].assert_not_called()

    def test_run_command_current_directory(self, mock_config, mock_debugger, mock_servers):
        with patch('quillion_cli.commands.run.load_config', return_value=mock_config), \
             patch('quillion_cli.commands.run.start_development_server') as mock_start_dev:
            
            from quillion_cli.commands.run import run_command
            with patch.object(Path, 'exists', return_value=True):
                run_command(name=None)
                
                mock_start_dev.assert_called_once()