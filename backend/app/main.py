"""Flask 应用入口。"""

import logging
import os
import sys

from flask import Flask, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from .api import comment_bp

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
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
