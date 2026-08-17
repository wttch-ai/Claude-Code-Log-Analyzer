"""写入默认模型价格（USD/1M tokens）。幂等：已存在则跳过。

用法：cd backend && .venv/Scripts/python -m scripts.seed_prices
"""

from datetime import datetime

from app.db import SessionLocal, init_db
from app.models import ModelPrice

DEFAULT_PRICES = [
    # model, input, cache_read, cache_creation, output, note
    ("claude-opus-4", 15.00, 1.50, 18.75, 75.00, "Anthropic 官方参考价"),
    ("claude-sonnet-4", 3.00, 0.30, 3.75, 15.00, "Anthropic 官方参考价"),
    ("claude-haiku-4-5", 1.00, 0.10, 1.25, 5.00, "Anthropic 官方参考价"),
    ("deepseek-v4-flash", 0.27, 0.027, 0.27, 1.10, "占位示例，请按实际账单修改"),
    ("deepseek-v4-pro", 0.55, 0.055, 0.55, 2.19, "占位示例，请按实际账单修改"),
    ("*", 1.00, 0.10, 1.00, 3.00, "默认兜底价（未单独配置的模型）"),
]


def seed() -> int:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    with SessionLocal() as db:
        for model, inp, cr, cc, out, note in DEFAULT_PRICES:
            exists = db.query(ModelPrice).filter(ModelPrice.model == model).first()
            if exists:
                continue
            db.add(
                ModelPrice(
                    model=model,
                    input_price=inp,
                    cache_read_price=cr,
                    cache_creation_price=cc,
                    output_price=out,
                    currency="USD",
                    note=note,
                    updated_at=now,
                )
            )
            inserted += 1
        db.commit()
    return inserted


if __name__ == "__main__":
    n = seed()
    print(f"seeded {n} prices (skipped existing)")
