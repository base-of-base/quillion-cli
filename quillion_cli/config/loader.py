import dataclasses
import tomllib
import typing as t
from pathlib import Path

import typer

from .models import (
    AppConfig,
    ServerConfig,
    HttpServerConfig,
    DevelopmentConfig,
    AssetsConfig,
)
from ..debug.debugger import debugger


def load_config(project_dir: str = "./") -> AppConfig:
    """Load and parse configuration from quillion.toml"""
    config_path = Path(project_dir) / "quillion.toml"

    if not config_path.exists():
        debugger.error("No quillion.toml found")
        raise typer.Exit(1)

    default_config = AppConfig()

    try:
        with config_path.open("rb") as f:
            user_config = tomllib.load(f)
    except Exception as e:
        debugger.error(f"Cannot load config: {e}")
        raise typer.Exit(1)

    def merge_configs(default, user):
        if isinstance(default, dict) and isinstance(user, dict):
            for k, v in user.items():
                if k in default:
                    default[k] = merge_configs(default[k], v)
                else:
                    default[k] = v
            return default
        return user

    default_dict = dataclasses.asdict(default_config)
    merged_dict = merge_configs(default_dict, user_config)

    return AppConfig(
        name=merged_dict["name"],
        version=merged_dict["version"],
        description=merged_dict["description"],
        server=ServerConfig(**merged_dict["server"]),
        http_server=HttpServerConfig(**merged_dict["http_server"]),
        development=DevelopmentConfig(**merged_dict["development"]),
        assets=AssetsConfig(**merged_dict["assets"]),
    )
