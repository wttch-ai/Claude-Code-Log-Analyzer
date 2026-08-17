"""FastAPI 入口。启动时建库、种子价格、后台增量扫描 + 定时自动扫描。"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api import aggregate, overview, prices, projects, scan, sessions, tiers
from .db import SessionLocal, init_db
from .models import ModelPrice
from .scanner.pipeline import run_scan

# 定时自动扫描：每 AUTO_SCAN_INTERVAL_S 秒增量扫描一次（run_scan 内部有锁防并发）
_auto_scan_stop = threading.Event()


def _auto_scan_loop() -> None:
    interval = config.AUTO_SCAN_INTERVAL_S
    while interval > 0 and not _auto_scan_stop.wait(interval):
        try:
            run_scan("incremental")
        except Exception as exc:  # noqa: BLE001 —— 定时循环不容崩溃
            import sys

            print(f"[auto-scan] incremental scan failed: {exc}", file=sys.stderr)


def _ensure_seed_prices() -> None:
    db = SessionLocal()
    try:
        if db.query(ModelPrice).count() == 0:
            from scripts.seed_prices import seed

            seed()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _ensure_seed_prices()
    if config.SCAN_ON_STARTUP:
        threading.Thread(target=run_scan, args=("incremental",), daemon=True).start()
    threading.Thread(target=_auto_scan_loop, daemon=True).start()
    yield
    _auto_scan_stop.set()


app = FastAPI(title="Claude Code Log Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    scan.router,
    overview.router,
    aggregate.router,
    projects.router,
    sessions.router,
    prices.router,
    tiers.router,
):
    app.include_router(router)
