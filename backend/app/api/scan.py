"""扫描触发与状态。"""

import threading

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ScanRun
from ..scanner.pipeline import is_scanning, latest_scan, run_scan

router = APIRouter(prefix="/api", tags=["scan"])


def _payload(scan: ScanRun | None) -> dict:
    if scan is None:
        return {"running": False, "has_run": False}
    return {
        "running": is_scanning(),
        "has_run": True,
        "id": scan.id,
        "mode": scan.mode,
        "status": scan.status,
        "error": scan.error,
        "started_at": scan.started_at,
        "finished_at": scan.finished_at,
        "projects_found": scan.projects_found,
        "main_files": scan.main_files,
        "subagent_files": scan.subagent_files,
        "entries_found": scan.entries_found,
        "new_entries": scan.new_entries,
        "unchanged_files": scan.unchanged_files,
        "updated_files": scan.updated_files,
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {"ok": True, "scanning": is_scanning(), "last_scan": _payload(latest_scan(db))}


@router.post("/scan")
def start_scan(mode: str = Query("incremental"), db: Session = Depends(get_db)):
    if mode not in ("incremental", "full"):
        return {"error": "mode must be incremental or full"}
    if is_scanning():
        return {"running": True, "message": "扫描进行中，忽略本次请求"}

    def _worker() -> None:
        run_scan(mode)

    threading.Thread(target=_worker, daemon=True).start()
    return {"running": True, "mode": mode}


@router.get("/scan/latest")
def scan_latest(db: Session = Depends(get_db)):
    return _payload(latest_scan(db))
