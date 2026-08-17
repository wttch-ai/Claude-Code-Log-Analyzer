"""会话时间轴（含子会话嵌套树）与单条消息详情。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import stats

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions/{session_id}/timeline")
def get_timeline(
    session_id: str,
    preview_len: int | None = Query(None, ge=100, le=20000),
    db: Session = Depends(get_db),
):
    data = stats.timeline(db, session_id, preview_len)
    if data is None:
        raise HTTPException(status_code=404, detail="session not found")
    return data


@router.get("/messages/{row_uuid}")
def get_message(
    row_uuid: str,
    preview_len: int | None = Query(None, ge=100, le=20000),
    db: Session = Depends(get_db),
):
    data = stats.message_detail(db, row_uuid, preview_len)
    if data is None:
        raise HTTPException(status_code=404, detail="message not found")
    return data
