"""定价服务：按 model_prices 实时计算成本。exact model → '*' 兜底 → priced:false。"""

from sqlalchemy.orm import Session

from ..models import ModelPrice

_FIELDS = ("input", "cache_read", "cache_creation", "output")


class PriceTable:
    def __init__(self, prices: dict[str, dict]):
        self._exact = prices
        self._fallback = prices.get("*")

    @classmethod
    def load(cls, db: Session) -> "PriceTable":
        rows = db.query(ModelPrice).all()
        d: dict[str, dict] = {}
        for r in rows:
            d[r.model] = {
                "input": r.input_price,
                "cache_read": r.cache_read_price,
                "cache_creation": r.cache_creation_price,
                "output": r.output_price,
                "currency": r.currency,
            }
        return cls(d)

    def cost(self, model: str | None, tokens: dict) -> dict:
        """tokens: {input, cache_read, cache_creation, output} → 成本明细。"""
        price = self._exact.get(model) if model else None
        if price is None:
            price = self._fallback
        if price is None:
            return {
                "total": None,
                "priced": False,
                "currency": None,
                "breakdown": None,
            }
        raw = {
            f: tokens.get(f, 0) * price[f] / 1_000_000 for f in _FIELDS
        }
        return {
            "total": sum(raw.values()),
            "priced": True,
            "currency": price["currency"],
            "breakdown": raw,
        }
