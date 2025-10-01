import functools
import http.server
import os
import socketserver
import ssl
import threading
import typing as t
from pathlib import Path
from socketserver import ThreadingMixIn

from ..debug.debugger import debugger


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self, *args, packages_dir: str = ".q", project_dir: str = ".", **kwargs
    ):
        self.packages_dir = packages_dir
        self.project_dir = project_dir
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def log_error(self, format, *args):
        pass

    def log_request(self, code="-", size="-"):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def guess_type(self, path):
        return super().guess_type(path)

    def translate_path(self, path):
        if ".." in path:
            self.send_error(400, "Invalid path")
            return None

        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]

        if path == "/":
            index_path = os.path.join(self.project_dir, self.packages_dir, "index.html")
            if os.path.exists(index_path):
                return index_path
            return super().translate_path("/")

        full_path = os.path.join(self.project_dir, self.packages_dir, path.lstrip("/"))

        if os.path.isdir(full_path):
            index_path = os.path.join(full_path, "index.html")
            if os.path.exists(index_path):
                return index_path
            return super().translate_path(path)

        if os.path.exists(full_path):
            return full_path

        if "." not in os.path.basename(path):
            index_path = os.path.join(self.project_dir, self.packages_dir, "index.html")
            if os.path.exists(index_path):
                return index_path

        return super().translate_path(path)


def start_http_server(
    config, project_dir: str
) -> t.Tuple[t.Optional[socketserver.TCPServer], t.Optional[threading.Thread]]:
    """Start HTTP server for static files"""
    http_cfg = config.http_server

    if not http_cfg.enabled:
        return None, None

    packages_path = Path(project_dir) / http_cfg.packages_dir
    packages_path.mkdir(exist_ok=True)

    original_cwd = os.getcwd()

    os.chdir(str(packages_path))

    try:
        handler = functools.partial(
            HTTPRequestHandler,
            packages_dir=http_cfg.packages_dir,
            project_dir=project_dir,
            directory=str(packages_path),
        )

        class ThreadedHTTPServer(ThreadingMixIn, socketserver.TCPServer):
            pass

        httpd = ThreadedHTTPServer((http_cfg.host, http_cfg.port), handler)

        if http_cfg.ssl and http_cfg.ssl_cert and http_cfg.ssl_key:
            cert_path = Path(http_cfg.ssl_cert)
            key_path = Path(http_cfg.ssl_key)

            if cert_path.exists() and key_path.exists():
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(cert_path, key_path)
                httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        def run_server():
            try:
                httpd.serve_forever()
            except Exception as e:
                debugger.error(f"HTTP server exc: {e}")
            finally:
                os.chdir(original_cwd)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        return httpd, server_thread

    except Exception as e:
        debugger.error(f"Cant start HTTP server: {e}")
        os.chdir(original_cwd)
        return None, None
