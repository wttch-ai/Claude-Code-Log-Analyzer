"""通用堆叠聚合：覆盖 skill / tool / project / model 视图。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import stats

router = APIRouter(prefix="/api", tags=["aggregate"])


@router.get("/aggregate")
def get_aggregate(
    dim: str = Query("skill", pattern="^(skill|tool|project|model)$"),
    granularity: str = Query("day", pattern="^(day|week)$"),
    start: str | None = None,
    end: str | None = None,
    project: int | None = None,
    session: str | None = None,
    db: Session = Depends(get_db),
):
    return stats.aggregate(
        db,
        dim=dim,
        granularity=granularity,
        start=start,
        end=end,
        project_id=project,
        session_id=session,
    )
