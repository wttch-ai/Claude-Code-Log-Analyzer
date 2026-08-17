"""FastAPI 入口。启动时建库、种子价格、后台增量扫描。"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api import aggregate, overview, prices, projects, scan, sessions
from .db import SessionLocal, init_db
from .models import ModelPrice
from .scanner.pipeline import run_scan


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
    yield


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
):
    app.include_router(router)
