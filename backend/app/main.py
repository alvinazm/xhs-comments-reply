"""Flask 应用入口。"""

import logging
import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from .api import comment_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("xhs-api")


def create_app() -> Flask:
    """创建 Flask 应用。"""
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    CORS(app)

    app.register_blueprint(comment_bp)

    @app.route("/")
    def index():
        """返回前端页面。"""
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        return {"message": "XHS API Server", "status": "running"}

    return app


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from config import Config

    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
