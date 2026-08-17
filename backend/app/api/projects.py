"""项目列表 / 详情 / 会话列表。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import stats

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects")
def list_projects(
    sort: str = Query("tokens", pattern="^(tokens|price|sessions|messages)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    offset: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    return stats.project_list(db, sort=sort, order=order, offset=offset, limit=limit)


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    data = stats.project_detail(db, project_id)
    if data is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="project not found")
    return data


@router.get("/projects/{project_id}/sessions")
def list_sessions(project_id: int, db: Session = Depends(get_db)):
    return stats.session_list(db, project_id)
