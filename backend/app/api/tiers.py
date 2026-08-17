"""按天/周 token 档位聚合：input / cache_read / cache_creation / output。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import stats

router = APIRouter(prefix="/api", tags=["tiers"])


@router.get("/tiers")
def get_tiers(
    granularity: str = Query("day", pattern="^(day|week)$"),
    start: str | None = None,
    end: str | None = None,
    project: int | None = None,
    session: str | None = None,
    db: Session = Depends(get_db),
):
    return stats.tier_series(
        db,
        granularity=granularity,
        start=start,
        end=end,
        project_id=project,
        session_id=session,
    )
