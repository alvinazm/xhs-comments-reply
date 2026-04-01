"""Flask 应用入口。"""

import asyncio
import logging
import os
import sys
from pathlib import Path
import threading

from dotenv import load_dotenv
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

from .api import comment_bp
from .services.ws_manager import start_ws_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

log = logging.getLogger("werkzeug")
log.setLevel(logging.WARNING)

logger = logging.getLogger("xhs-api")

scheduler = None


def cleanup_job():
    """定时清理超过20天的CSV文件。"""
    from .services.csv_storage import cleanup_old_csvs, DOWNLOAD_DIR

    deleted = cleanup_old_csvs(days=20)
    if deleted > 0:
        logger.info(f"清理了 {deleted} 个过期的 CSV 文件")


def create_app() -> Flask:
    """创建 Flask 应用。"""
    from .services.csv_storage import DOWNLOAD_DIR

    app = Flask(__name__, static_folder="static", static_url_path="/static")
    CORS(app)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    app.register_blueprint(comment_bp)

    @app.route("/")
    def index():
        """返回前端页面。"""
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        return {"message": "XHS API Server", "status": "running"}

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        """服务 connector 目录下的脚本文件"""
        connector_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "connector"
        )
        return send_from_directory(connector_dir, filename)

    @app.route("/api/client-status")
    def client_status():
        """获取客户端连接状态"""
        from .services.ws_manager import is_any_client_connected

        return jsonify({"connected": is_any_client_connected()})

    return app


def start_scheduler():
    """启动定时任务调度器。"""
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_job, "cron", hour=3, minute=0)
    scheduler.start()
    logger.info("定时任务调度器已启动")


if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from config import Config

    app = create_app()
    start_scheduler()

    def run_ws():
        asyncio.run(start_ws_server())

    ws_thread = threading.Thread(target=run_ws, daemon=True)
    ws_thread.start()

    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
