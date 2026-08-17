"""全局概览。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import stats

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    return stats.overview(db)
