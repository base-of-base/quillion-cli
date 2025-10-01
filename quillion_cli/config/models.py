import typing as t
from dataclasses import dataclass, field


@dataclass
class DebugConfig:
    quiet: bool = False
    no_color: bool = False
    no_figlet: bool = False


@dataclass
class ServerConfig:
    entry_point: str = "app.py"
    host: str = "127.0.0.1"
    port: int = 1337
    debug: bool = True
    reload: bool = True


@dataclass
class AssetsConfig:
    host: str = "127.0.0.1"
    port: int = 1338
    path: str = ""


@dataclass
class HttpServerConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    ssl: bool = False
    ssl_cert: t.Optional[str] = None
    ssl_key: t.Optional[str] = None
    packages_dir: str = ".q"


@dataclass
class DevelopmentConfig:
    watch_dirs: list[str] = field(default_factory=lambda: ["."])
    ignore_patterns: list[str] = field(
        default_factory=lambda: [
            "__pycache__",
            "*.log",
            "*.tmp",
            ".git",
        ]
    )
    file_extensions: list[str] = field(
        default_factory=lambda: [".py", ".toml", ".html", ".css", ".js", ".json"]
    )
    delay: float = 1.0


@dataclass
class AppConfig:
    name: str = "my-awesome-app"
    version: str = "0.1.0"
    description: str = "Q web app"
    server: ServerConfig = field(default_factory=ServerConfig)
    http_server: HttpServerConfig = field(default_factory=HttpServerConfig)
    development: DevelopmentConfig = field(default_factory=DevelopmentConfig)
    assets: AssetsConfig = field(default_factory=AssetsConfig)
