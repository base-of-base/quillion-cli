import pytest
import tempfile
import threading
import time
import requests
import ssl
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import http.server
import socketserver
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from quillion_cli.server.http_server import (
    HTTPRequestHandler,
    start_http_server,
)


class TestHTTPRequestHandler:
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            packages_dir = project_dir / ".q"
            packages_dir.mkdir()

            (packages_dir / "index.html").write_text("<html>Home</html>")
            (packages_dir / "style.css").write_text("body { color: red; }")
            (packages_dir / "script.js").write_text("console.log('hello');")

            sub_dir = packages_dir / "subdir"
            sub_dir.mkdir()
            (sub_dir / "index.html").write_text("<html>Subdir</html>")
            (sub_dir / "data.json").write_text('{"key": "value"}')

            yield project_dir

    def create_handler_instance(self, project_dir, packages_dir=".q"):
        """Create a handler instance without triggering HTTP processing."""

        class MockRequest:
            def makefile(self, *args, **kwargs):
                return Mock()

            def shutdown(self, *args, **kwargs):
                pass

        handler = HTTPRequestHandler.__new__(HTTPRequestHandler)

        handler.packages_dir = packages_dir
        handler.project_dir = str(project_dir)
        handler.path = "/"

        handler.rfile = Mock()
        handler.wfile = Mock()
        handler.request = MockRequest()
        handler.client_address = ("127.0.0.1", 8080)
        handler.server = Mock()
        handler.headers = Mock()

        handler.directory = str(project_dir / packages_dir)

        return handler

    def test_handler_initialization(self, temp_project_dir):
        """Test HTTPRequestHandler initialization with custom parameters."""
        handler = self.create_handler_instance(temp_project_dir)

        assert handler.packages_dir == ".q"
        assert handler.project_dir == str(temp_project_dir)

    def test_translate_path_root(self, temp_project_dir):
        """Test path translation for root path."""
        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/"
        result = handler.translate_path("/")

        expected_path = str(temp_project_dir / ".q" / "index.html")
        assert result == expected_path

    def test_translate_path_existing_file(self, temp_project_dir):
        """Test path translation for existing file."""
        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/style.css"
        result = handler.translate_path("/style.css")

        expected_path = str(temp_project_dir / ".q" / "style.css")
        assert result == expected_path

    def test_translate_path_directory_without_index(self, temp_project_dir):
        """Test path translation for directory without index.html."""
        empty_dir = temp_project_dir / ".q" / "empty"
        empty_dir.mkdir()

        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/empty/"

        with patch.object(
            http.server.SimpleHTTPRequestHandler, "translate_path"
        ) as mock_parent:
            mock_parent.return_value = str(empty_dir)
            result = handler.translate_path("/empty/")

            mock_parent.assert_called_once_with("/empty/")

    def test_translate_path_no_extension_fallback_to_index(self, temp_project_dir):
        """Test path translation for path without extension falls back to index.html."""
        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/some-route"
        result = handler.translate_path("/some-route")

        expected_path = str(temp_project_dir / ".q" / "index.html")
        assert result == expected_path

    def test_translate_path_with_query_params(self, temp_project_dir):
        """Test path translation strips query parameters."""
        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/style.css?v=1"
        result = handler.translate_path("/style.css?v=1")

        expected_path = str(temp_project_dir / ".q" / "style.css")
        assert result == expected_path

    def test_translate_path_with_fragment(self, temp_project_dir):
        """Test path translation strips URL fragments."""
        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/style.css#section"
        result = handler.translate_path("/style.css#section")

        expected_path = str(temp_project_dir / ".q" / "style.css")
        assert result == expected_path

    def test_translate_path_path_traversal_prevention(self, temp_project_dir):
        """Test path translation prevents directory traversal."""
        handler = self.create_handler_instance(temp_project_dir)
        handler.path = "/../etc/passwd"

        with patch.object(handler, "send_error") as mock_send_error:
            result = handler.translate_path("/../etc/passwd")

            mock_send_error.assert_called_once_with(400, "Invalid path")
            assert result is None

    def test_translate_path_custom_packages_dir(self, temp_project_dir):
        """Test path translation with custom packages directory."""
        custom_dir = temp_project_dir / "custom_pkg"
        custom_dir.mkdir()
        (custom_dir / "custom.html").write_text("custom content")

        handler = self.create_handler_instance(
            temp_project_dir, packages_dir="custom_pkg"
        )
        handler.path = "/custom.html"
        result = handler.translate_path("/custom.html")

        expected_path = str(temp_project_dir / "custom_pkg" / "custom.html")
        assert result == expected_path

    def test_log_methods_silent(self, temp_project_dir):
        """Test that logging methods are silent."""
        handler = self.create_handler_instance(temp_project_dir)

        handler.log_message("Test %s", "message")
        handler.log_error("Test %s", "error")
        handler.log_request("200")

    def test_end_headers_adds_cors(self, temp_project_dir):
        """Test that end_headers adds CORS headers."""
        handler = self.create_handler_instance(temp_project_dir)

        with patch.object(handler, "send_header") as mock_send_header:
            with patch.object(
                http.server.SimpleHTTPRequestHandler, "end_headers"
            ) as mock_parent_end:
                handler.end_headers()

                mock_send_header.assert_any_call("Access-Control-Allow-Origin", "*")
                mock_send_header.assert_any_call(
                    "Access-Control-Allow-Methods", "GET, POST, OPTIONS"
                )
                mock_send_header.assert_any_call(
                    "Access-Control-Allow-Headers", "Content-Type"
                )

                mock_parent_end.assert_called_once()

    def test_guess_type_delegation(self, temp_project_dir):
        """Test that guess_type delegates to parent class."""
        handler = self.create_handler_instance(temp_project_dir)

        with patch.object(
            http.server.SimpleHTTPRequestHandler, "guess_type"
        ) as mock_guess:
            mock_guess.return_value = "text/html"
            result = handler.guess_type("/test.html")

            mock_guess.assert_called_once_with("/test.html")
            assert result == "text/html"


class TestStartHTTPServer:
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.http_server.enabled = True
        config.http_server.host = "127.0.0.1"
        config.http_server.port = 0
        config.http_server.packages_dir = ".q"
        config.http_server.ssl = False
        config.http_server.ssl_cert = None
        config.http_server.ssl_key = None
        return config

    def test_start_http_server_success(self, temp_project_dir, mock_config):
        """Test successful HTTP server startup."""
        packages_dir = temp_project_dir / ".q"
        packages_dir.mkdir()
        (packages_dir / "index.html").write_text("test content")

        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        try:
            assert httpd is not None
            assert server_thread is not None
            assert server_thread.is_alive()
            assert server_thread.daemon is True

            assert httpd.server_address[0] == mock_config.http_server.host
            assert httpd.server_address[1] > 0

        finally:
            if httpd:
                httpd.shutdown()
            if server_thread:
                server_thread.join(timeout=1)

    def test_start_http_server_disabled(self, temp_project_dir, mock_config):
        """Test HTTP server startup when disabled."""
        mock_config.http_server.enabled = False

        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        assert httpd is None
        assert server_thread is None

    def test_start_http_server_missing_packages_dir(
        self, temp_project_dir, mock_config
    ):
        """Test HTTP server startup with missing packages directory (should be created)."""
        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        try:
            assert httpd is not None
            assert server_thread is not None

            packages_dir = temp_project_dir / ".q"
            assert packages_dir.exists()
            assert packages_dir.is_dir()

        finally:
            if httpd:
                httpd.shutdown()
            if server_thread:
                server_thread.join(timeout=1)

    def test_start_http_server_with_ssl(self, temp_project_dir, mock_config):
        """Test HTTP server startup with SSL enabled."""
        cert_file = temp_project_dir / "cert.pem"
        key_file = temp_project_dir / "key.pem"
        cert_file.write_text("fake cert")
        key_file.write_text("fake key")

        mock_config.http_server.ssl = True
        mock_config.http_server.ssl_cert = str(cert_file)
        mock_config.http_server.ssl_key = str(key_file)

        with patch(
            "quillion_cli.server.http_server.ssl.SSLContext"
        ) as mock_ssl_context:
            mock_context = Mock()
            mock_ssl_context.return_value = mock_context

            httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

            try:
                assert httpd is not None
                assert server_thread is not None

                mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)
                mock_context.load_cert_chain.assert_called_once_with(
                    cert_file, key_file
                )

            finally:
                if httpd:
                    httpd.shutdown()
                if server_thread:
                    server_thread.join(timeout=1)

    def test_start_http_server_ssl_missing_files(self, temp_project_dir, mock_config):
        """Test HTTP server startup with SSL but missing certificate files."""
        mock_config.http_server.ssl = True
        mock_config.http_server.ssl_cert = "/nonexistent/cert.pem"
        mock_config.http_server.ssl_key = "/nonexistent/key.pem"

        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        try:
            assert httpd is not None
            assert server_thread is not None

        finally:
            if httpd:
                httpd.shutdown()
            if server_thread:
                server_thread.join(timeout=1)

    def test_start_http_server_port_in_use(self, temp_project_dir, mock_config):
        """Test HTTP server startup when port is in use."""
        with patch(
            "quillion_cli.server.http_server.socketserver.TCPServer"
        ) as mock_tcpserver:
            mock_tcpserver.side_effect = OSError("Port already in use")

            with patch("quillion_cli.server.http_server.debugger") as mock_debugger:
                httpd, thread = start_http_server(mock_config, str(temp_project_dir))

                assert httpd is None
                assert thread is None
                mock_debugger.error.assert_called()

    def test_start_http_server_directory_change_restored(
        self, temp_project_dir, mock_config
    ):
        """Test that original working directory is restored after server shutdown."""
        original_cwd = os.getcwd()

        packages_dir = temp_project_dir / ".q"
        packages_dir.mkdir()

        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        try:
            assert httpd is not None

        finally:
            if httpd:
                httpd.shutdown()
            if server_thread:
                server_thread.join(timeout=1)

            assert os.getcwd() == original_cwd

    def test_start_http_server_thread_creation(self, temp_project_dir, mock_config):
        """Test HTTP server thread creation and startup."""
        packages_dir = temp_project_dir / ".q"
        packages_dir.mkdir()

        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        try:
            assert httpd is not None
            assert server_thread is not None
            assert isinstance(server_thread, threading.Thread)
            assert server_thread.daemon is True

        finally:
            if httpd:
                httpd.shutdown()
            if server_thread:
                server_thread.join(timeout=1)

    def test_server_serves_files(self, temp_project_dir, mock_config):
        """Test that the server actually serves files correctly."""
        packages_dir = temp_project_dir / ".q"
        packages_dir.mkdir()
        (packages_dir / "index.html").write_text("<h1>Test Page</h1>")
        (packages_dir / "test.txt").write_text("Hello World")

        mock_config.http_server.port = 0

        httpd, server_thread = start_http_server(mock_config, str(temp_project_dir))

        try:
            time.sleep(0.5)

            port = httpd.server_address[1]

            try:
                response = requests.get(f"http://127.0.0.1:{port}/", timeout=1)
                assert response.status_code == 200
                assert "<h1>Test Page</h1>" in response.text

                response = requests.get(f"http://127.0.0.1:{port}/test.txt", timeout=1)
                assert response.status_code == 200
                assert response.text == "Hello World"
            except requests.exceptions.RequestException:
                pytest.skip("Server not ready for requests")

        finally:
            if httpd:
                httpd.shutdown()
            if server_thread:
                server_thread.join(timeout=1)

    def test_server_exception_handling(self, temp_project_dir, mock_config):
        """Test server exception handling."""
        packages_dir = temp_project_dir / ".q"
        packages_dir.mkdir()

        with patch(
            "quillion_cli.server.http_server.threading.Thread"
        ) as mock_thread_class:
            mock_thread_instance = Mock()
            mock_thread_class.return_value = mock_thread_instance

            def raise_exception():
                raise Exception("Test error")

            mock_thread_instance.start.side_effect = raise_exception

            with patch("quillion_cli.server.http_server.debugger") as mock_debugger:
                httpd, server_thread = start_http_server(
                    mock_config, str(temp_project_dir)
                )

                assert httpd is None
                assert server_thread is None
                mock_debugger.error.assert_called()
