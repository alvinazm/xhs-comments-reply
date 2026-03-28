import json
import os
from pathlib import Path


def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


_config = load_config()


class Config:
    _chrome_cfg = _config.get("chrome") 
    _backend_cfg = _config.get("backend") 
    _frontend_cfg = _config.get("frontend")

    CHROME_HOST = os.getenv("CHROME_HOST", _chrome_cfg.get("host"))
    CHROME_PORT = int(os.getenv("CHROME_PORT", _chrome_cfg.get("port")))

    FLASK_HOST = os.getenv("FLASK_HOST", _backend_cfg.get("host"))
    FLASK_PORT = int(os.getenv("FLASK_PORT", _backend_cfg.get("port")))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    VITE_PORT = int(os.getenv("VITE_PORT", _frontend_cfg.get("port")))
