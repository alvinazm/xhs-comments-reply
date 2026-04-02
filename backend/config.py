import json
import os
import yaml
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def load_yaml_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def load_json_config():
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


_yaml_config = load_yaml_config()
_json_config = load_json_config()


class Config:
    _chrome_cfg = _json_config.get("chrome")
    _backend_cfg = _json_config.get("backend")
    _frontend_cfg = _json_config.get("frontend")

    CHROME_HOST = os.getenv(
        "CHROME_HOST", _chrome_cfg.get("host") if _chrome_cfg else None
    )
    CHROME_PORT = int(
        os.getenv("CHROME_PORT", _chrome_cfg.get("port") if _chrome_cfg else 9222)
    )

    FLASK_HOST = os.getenv(
        "FLASK_HOST", _backend_cfg.get("host") if _backend_cfg else "0.0.0.0"
    )
    FLASK_PORT = int(
        os.getenv("FLASK_PORT", _backend_cfg.get("port") if _backend_cfg else 5000)
    )
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    VITE_PORT = int(
        os.getenv("VITE_PORT", _frontend_cfg.get("port") if _frontend_cfg else 5173)
    )

    _ws_cfg = _json_config.get("ws_server")
    WS_SERVER_HOST = os.getenv(
        "WS_SERVER_HOST", _ws_cfg.get("host") if _ws_cfg else "0.0.0.0"
    )
    WS_SERVER_PORT = int(
        os.getenv("WS_SERVER_PORT", _ws_cfg.get("port") if _ws_cfg else 8765)
    )

    _server_cfg = _json_config.get("server")
    SERVER_HOST = os.getenv(
        "SERVER_HOST", _server_cfg.get("host") if _server_cfg else "localhost"
    )
    SERVER_PORT = int(
        os.getenv("SERVER_PORT", _server_cfg.get("port") if _server_cfg else 5000)
    )

    MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")

    PROMPT = _yaml_config.get("prompt", {})
