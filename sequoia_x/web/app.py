"""FastAPI 应用工厂。"""

import logging
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sequoia_x.core.config import get_settings
from sequoia_x.data.engine import DataEngine

_BASE_DIR = Path(__file__).resolve().parent
_TEMPLATE_DIR = _BASE_DIR / "templates"
_STATIC_DIR = _BASE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Sequoia-X Dashboard", version="2.0.0")

    # 挂载静态文件和模板
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.state.templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

    # 注册路由
    from sequoia_x.web.routes.pages import router as pages_router
    from sequoia_x.web.routes.api import router as api_router

    app.include_router(pages_router)
    app.include_router(api_router, prefix="/api")

    @app.on_event("startup")
    def on_startup() -> None:
        from sequoia_x.web.services import WebServices, RingBufferHandler

        settings = get_settings()
        engine = DataEngine(settings)
        app.state.settings = settings
        app.state.engine = engine
        app.state.services = WebServices(settings, engine)

        # SQLite WAL 模式：允许读写并发
        with sqlite3.connect(engine.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

        # 日志环形缓冲区 — 挂到 sequoia_x logger 上（其 propagate=False，root logger 收不到）
        handler = RingBufferHandler(maxlen=500)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
        logging.getLogger("sequoia_x").addHandler(handler)
        app.state.log_handler = handler

    return app
