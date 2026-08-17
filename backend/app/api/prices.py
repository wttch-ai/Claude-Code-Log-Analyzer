"""模型价格配置 CRUD。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Message, ModelPrice

router = APIRouter(prefix="/api", tags=["prices"])


class PriceIn(BaseModel):
    """部分更新语义：未提供的字段保留原值。"""

    input_price: float | None = Field(None, ge=0)
    cache_read_price: float | None = Field(None, ge=0)
    cache_creation_price: float | None = Field(None, ge=0)
    output_price: float | None = Field(None, ge=0)
    currency: str | None = None
    note: str | None = None


def _row_payload(r: ModelPrice) -> dict:
    return {
        "model": r.model,
        "input_price": r.input_price,
        "cache_read_price": r.cache_read_price,
        "cache_creation_price": r.cache_creation_price,
        "output_price": r.output_price,
        "currency": r.currency,
        "note": r.note,
        "updated_at": r.updated_at,
    }


@router.get("/prices")
def list_prices(db: Session = Depends(get_db)):
    rows = db.query(ModelPrice).order_by(ModelPrice.model).all()
    return [_row_payload(r) for r in rows]


@router.put("/prices/{model}")
def upsert_price(model: str, body: PriceIn, db: Session = Depends(get_db)):
    r = db.query(ModelPrice).filter(ModelPrice.model == model).first()
    if r is None:
        r = ModelPrice(model=model, currency="USD")
        db.add(r)
    changed = False
    for field in ("input_price", "cache_read_price", "cache_creation_price", "output_price"):
        v = getattr(body, field)
        if v is not None and getattr(r, field) != v:
            setattr(r, field, v)
            changed = True
    if body.currency is not None and r.currency != body.currency:
        r.currency = body.currency
        changed = True
    if body.note is not None and r.note != body.note:
        r.note = body.note
        changed = True
    if changed:
        r.updated_at = datetime.now().isoformat(timespec="seconds")
    db.commit()
    db.refresh(r)
    return _row_payload(r)


@router.delete("/prices/{model}")
def delete_price(model: str, db: Session = Depends(get_db)):
    if model == "*":
        raise HTTPException(status_code=400, detail="cannot delete fallback '*'")
    r = db.query(ModelPrice).filter(ModelPrice.model == model).first()
    if r is None:
        raise HTTPException(status_code=404, detail="price not found")
    db.delete(r)
    db.commit()
    return {"deleted": model}


@router.post("/prices/default")
def apply_default(db: Session = Depends(get_db)):
    """以 '*' 兜底价批量补全数据中出现但未配置价格的模型。"""
    fallback = db.query(ModelPrice).filter(ModelPrice.model == "*").first()
    if fallback is None:
        raise HTTPException(status_code=400, detail="no fallback '*' price")
    now = datetime.now().isoformat(timespec="seconds")
    applied = 0
    for (m,) in db.query(Message.model).distinct().all():
        if not m or m == "*":
            continue
        if db.query(ModelPrice).filter(ModelPrice.model == m).first():
            continue
        db.add(
            ModelPrice(
                model=m,
                input_price=fallback.input_price,
                cache_read_price=fallback.cache_read_price,
                cache_creation_price=fallback.cache_creation_price,
                output_price=fallback.output_price,
                currency=fallback.currency,
                note=f"copied from '*' at {now}",
                updated_at=now,
            )
        )
        applied += 1
    db.commit()
    return {"applied": applied}


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    rows = (
        db.query(Message.model)
        .filter(Message.model.is_not(None))
        .distinct()
        .order_by(Message.model)
        .all()
    )
    return [m for (m,) in rows]
