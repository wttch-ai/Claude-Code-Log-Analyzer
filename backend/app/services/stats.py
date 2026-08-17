"""统计查询：overview / aggregate / projects / sessions / timeline / message_detail。

所有响应同时含 tokens 与 price（按当前 model_prices 实时计算）。
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config
from ..models import (
    Compaction,
    Entry,
    Message,
    Project,
    Session as SessionModel,
    SubagentSession,
    ToolCall,
    ToolResult,
)
from .pricing import PriceTable

_FIELDS = ("input", "cache_read", "cache_creation", "output")
_SUM_COLS = (
    func.sum(Message.input_tokens),
    func.sum(Message.cache_read_tokens),
    func.sum(Message.cache_creation_tokens),
    func.sum(Message.output_tokens),
    func.sum(Message.total_tokens),
)


def _tokens_dict(i, cr, cc, o) -> dict:
    return {
        "input": int(i or 0),
        "cache_read": int(cr or 0),
        "cache_creation": int(cc or 0),
        "output": int(o or 0),
        "total": int(i or 0) + int(cr or 0) + int(cc or 0) + int(o or 0),
    }


def _safe_json_loads(s: str | None):
    """JSON 容错解析：非法 JSON 按原始字符串返回。"""
    if not s:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


def _local_today() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")


# ---------------------------------------------------------------- overview

def overview(db: Session) -> dict:
    pt = PriceTable.load(db)

    def _agg(q):
        row = q.first()
        if not row:
            return _tokens_dict(0, 0, 0, 0)
        return _tokens_dict(row[0], row[1], row[2], row[3])

    base = db.query(*_SUM_COLS)
    totals = _agg(base)
    today_s = _local_today()
    today = _agg(base.filter(Message.day_local == today_s))
    week_start = (datetime.now().astimezone() - timedelta(days=6)).strftime("%Y-%m-%d")
    week = _agg(base.filter(Message.day_local >= week_start))

    # 模型分布
    model_rows = (
        db.query(Message.model, *_SUM_COLS)
        .group_by(Message.model)
        .order_by(func.sum(Message.total_tokens).desc())
        .all()
    )
    models = []
    for mrow in model_rows:
        model = mrow[0]
        toks = _tokens_dict(mrow[1], mrow[2], mrow[3], mrow[4])
        cost = pt.cost(model, toks)
        models.append(
            {
                "model": model,
                "tokens": toks,
                "price": cost,
                "cost_share": None,
            }
        )
    priced_total = sum(m["price"]["total"] for m in models if m["price"]["priced"])
    for m in models:
        if m["price"]["priced"] and priced_total:
            m["cost_share"] = round(m["price"]["total"] / priced_total, 4)

    cache_read_ratio = round(totals["cache_read"] / totals["total"], 4) if totals["total"] else 0

    comp_row = db.query(
        func.count(Compaction.id),
        func.sum(Compaction.dropped_tokens),
    ).first()

    return {
        "totals": {"tokens": totals, "price": pt.cost(None, totals)},
        "today": {"tokens": today, "price": pt.cost(None, today)},
        "week": {"tokens": week, "price": pt.cost(None, week)},
        "projects_count": db.query(Project).count(),
        "main_sessions": db.query(SessionModel).count(),
        "subagent_sessions": db.query(SubagentSession).count(),
        "messages": db.query(Message).count(),
        "cache_read_ratio": cache_read_ratio,
        "models": models,
        "compactions": {"count": comp_row[0] or 0, "dropped_tokens": comp_row[1] or 0},
    }


# ---------------------------------------------------------------- aggregate

_DIM_COL = {
    "skill": Message.rollup_bucket,
    "tool": Message.primary_tool,
    "project": Project.name,
    "model": Message.model,
}


def aggregate(
    db: Session,
    dim: str,
    granularity: str,
    start: str | None = None,
    end: str | None = None,
    project_id: int | None = None,
    session_id: str | None = None,
) -> dict:
    if dim not in _DIM_COL:
        raise ValueError(f"dim must be one of {list(_DIM_COL)}")

    if granularity == "week":
        date_expr = func.strftime("%G-W%V", Message.day_local)
    else:
        date_expr = Message.day_local

    q = (
        db.query(
            date_expr.label("d"),
            _DIM_COL[dim].label("k"),
            Message.model,
            func.sum(Message.input_tokens),
            func.sum(Message.cache_read_tokens),
            func.sum(Message.cache_creation_tokens),
            func.sum(Message.output_tokens),
            func.sum(Message.total_tokens),
        )
        .join(Project, Project.id == Message.project_id)
        .group_by("d", "k", Message.model)
        .order_by("d")
    )
    if start:
        q = q.filter(Message.day_local >= start)
    if end:
        q = q.filter(Message.day_local <= end)
    if project_id:
        q = q.filter(Message.project_id == project_id)
    if session_id:
        q = q.filter(Message.session_id == session_id)

    pt = PriceTable.load(db)
    cells: dict[tuple[str, str], dict] = {}
    prices: dict[tuple[str, str], float] = {}
    for d, k, model, inp, cr, cc, out, _tot in q.all():
        key = (k or "(none)", d)
        c = cells.setdefault(
            key,
            {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0},
        )
        c["input"] += int(inp or 0)
        c["cache_read"] += int(cr or 0)
        c["cache_creation"] += int(cc or 0)
        c["output"] += int(out or 0)
        cost = pt.cost(model, _tokens_dict(inp, cr, cc, out))
        if cost["priced"]:
            prices[key] = prices.get(key, 0.0) + cost["total"]

    # 日期序列（day 粒度补全连续天）
    dates = sorted({d for (_k, d) in cells})
    if granularity == "day" and dates and len(dates) < 370:
        d0 = date.fromisoformat(dates[0])
        d1 = date.fromisoformat(dates[-1])
        full = []
        d = d0
        while d <= d1 and len(full) < 370:
            full.append(d.isoformat())
            d += timedelta(days=1)
        dates = full

    # 组装 series（按总 token 降序，>12 并入 Other）
    # values 元素 = {tokens: 当日总量, price: 当日价格}，前端按显示模式择取
    series_map: dict[str, dict] = {}
    for (k, d) in cells:
        s = series_map.setdefault(k, {"by_date": {}, "tokens": 0, "price": 0.0})
        toks = cells[(k, d)]
        day_total = (
            toks["input"] + toks["cache_read"] + toks["cache_creation"] + toks["output"]
        )
        s["by_date"][d] = {
            "tokens": day_total,
            "price": round(prices.get((k, d), 0.0), 6),
        }
        s["tokens"] += day_total
        s["price"] += prices.get((k, d), 0.0)

    ordered = sorted(series_map.items(), key=lambda kv: kv[1]["tokens"], reverse=True)
    series = []
    other_by_date: dict[str, dict] = {}
    other_tokens = other_price = 0
    for idx, (name, s) in enumerate(ordered):
        if idx >= 12:
            for d, cell in s["by_date"].items():
                oc = other_by_date.setdefault(d, {"tokens": 0, "price": 0.0})
                oc["tokens"] += cell["tokens"]
                oc["price"] += cell["price"]
            other_tokens += s["tokens"]
            other_price += s["price"]
            continue
        series.append(
            {
                "name": name,
                "values": [
                    s["by_date"].get(d, {"tokens": 0, "price": 0.0}) for d in dates
                ],
                "total_tokens": s["tokens"],
                "total_price": round(s["price"], 6),
            }
        )
    if other_by_date:
        series.append(
            {
                "name": "Other",
                "values": [
                    other_by_date.get(d, {"tokens": 0, "price": 0.0}) for d in dates
                ],
                "total_tokens": other_tokens,
                "total_price": round(other_price, 6),
            }
        )

    total_tokens = sum(s["total_tokens"] for s in series)
    total_price = sum(s["total_price"] for s in series)
    return {
        "dim": dim,
        "granularity": granularity,
        "dates": dates,
        "series": series,
        "total_tokens": total_tokens,
        "total_price": round(total_price, 6),
    }


# ---------------------------------------------------------------- tiers

def tier_series(
    db: Session,
    granularity: str,
    start: str | None = None,
    end: str | None = None,
    project_id: int | None = None,
    session_id: str | None = None,
) -> dict:
    """按天/周聚合各 token 档位（input / cache_read / cache_creation / output）。

    每档独立 series（含 tokens 与 price），前端按「输入 / 输出 / Cache」三分类合并展示，
    亦可拆细。与 aggregate 不同：这里维度即档位，不含 skill/tool 等归因桶。
    """
    if granularity == "week":
        date_expr = func.strftime("%G-W%V", Message.day_local)
    else:
        date_expr = Message.day_local

    q = (
        db.query(
            date_expr.label("d"),
            Message.model,
            func.sum(Message.input_tokens),
            func.sum(Message.cache_read_tokens),
            func.sum(Message.cache_creation_tokens),
            func.sum(Message.output_tokens),
        )
        .group_by("d", Message.model)
        .order_by("d")
    )
    if start:
        q = q.filter(Message.day_local >= start)
    if end:
        q = q.filter(Message.day_local <= end)
    if project_id:
        q = q.filter(Message.project_id == project_id)
    if session_id:
        q = q.filter(Message.session_id == session_id)

    tiers = ("input", "cache_read", "cache_creation", "output")
    pt = PriceTable.load(db)
    # d -> tier -> {"tokens": int, "price": float}
    acc: dict[str, dict[str, dict]] = {}
    for d, model, inp, cr, cc, out in q.all():
        toks = _tokens_dict(inp, cr, cc, out)
        day = acc.setdefault(d, {t: {"tokens": 0, "price": 0.0} for t in tiers})
        cost = pt.cost(model, toks)
        bd = cost["breakdown"] or {t: 0.0 for t in tiers}
        for t in tiers:
            day[t]["tokens"] += toks[t]
            if cost["priced"]:
                day[t]["price"] += bd.get(t, 0.0)

    # 日期序列（day 粒度补全连续天）
    dates = sorted(acc)
    if granularity == "day" and dates and len(dates) < 370:
        d0 = date.fromisoformat(dates[0])
        d1 = date.fromisoformat(dates[-1])
        full = []
        d = d0
        while d <= d1 and len(full) < 370:
            full.append(d.isoformat())
            d += timedelta(days=1)
        dates = full

    series = []
    for t in tiers:
        series.append(
            {
                "name": t,
                "values": [
                    {"tokens": 0, "price": 0.0}
                    if d not in acc or t not in acc[d]
                    else {
                        "tokens": acc[d][t]["tokens"],
                        "price": round(acc[d][t]["price"], 6),
                    }
                    for d in dates
                ],
                "total_tokens": sum(acc.get(d, {}).get(t, {"tokens": 0})["tokens"] for d in dates),
                "total_price": round(sum(acc.get(d, {}).get(t, {"price": 0.0})["price"] for d in dates), 6),
            }
        )

    total_tokens = sum(s["total_tokens"] for s in series)
    total_price = sum(s["total_price"] for s in series)
    return {
        "granularity": granularity,
        "dates": dates,
        "series": series,
        "total_tokens": total_tokens,
        "total_price": round(total_price, 6),
    }


# ---------------------------------------------------------------- projects

def project_list(
    db: Session, sort: str = "tokens", order: str = "desc", offset: int = 0, limit: int = 100
) -> dict:
    pt = PriceTable.load(db)
    # 项目基础 + 会话数（一次查询）
    rows = (
        db.query(
            Project.id,
            Project.slug,
            Project.name,
            Project.cwd,
            Project.last_seen_at,
            func.count(SessionModel.id),
            func.sum(SessionModel.message_count),
            func.sum(SessionModel.subagent_count),
        )
        .outerjoin(SessionModel, SessionModel.project_id == Project.id)
        .group_by(Project.id)
        .all()
    )
    # 每项目按 model 的 token 汇总（一次查询）
    msg_rows = (
        db.query(
            Message.project_id,
            Message.model,
            func.sum(Message.input_tokens),
            func.sum(Message.cache_read_tokens),
            func.sum(Message.cache_creation_tokens),
            func.sum(Message.output_tokens),
        )
        .group_by(Message.project_id, Message.model)
        .all()
    )
    per_proj: dict[int, dict] = {}
    for pid, model, inp, cr, cc, out in msg_rows:
        e = per_proj.setdefault(
            pid, {"tokens": {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}, "price": 0.0, "priced": False}
        )
        toks = _tokens_dict(inp, cr, cc, out)
        for f in _FIELDS:
            e["tokens"][f] += toks[f]
        cost = pt.cost(model, toks)
        if cost["priced"]:
            e["price"] += cost["total"]
            e["priced"] = True

    items = []
    for pid, slug, name, cwd, last_seen, n_sess, n_msg, n_sub in rows:
        e = per_proj.get(pid, {"tokens": _tokens_dict(0, 0, 0, 0), "price": 0.0, "priced": False})
        toks = e["tokens"]
        items.append(
            {
                "id": pid,
                "slug": slug,
                "name": name or slug,
                "cwd": cwd,
                "last_seen_at": last_seen,
                "sessions": int(n_sess or 0),
                "messages": int(n_msg or 0),
                "subagents": int(n_sub or 0),
                "tokens": {
                    **toks,
                    "total": toks["input"] + toks["cache_read"] + toks["cache_creation"] + toks["output"],
                },
                "price": {"total": round(e["price"], 6), "priced": e["priced"], "currency": "USD"},
            }
        )

    sort_key = {
        "tokens": lambda x: x["tokens"]["total"],
        "price": lambda x: x["price"]["total"] or 0,
        "sessions": lambda x: x["sessions"],
        "messages": lambda x: x["messages"],
    }.get(sort, lambda x: x["tokens"]["total"])
    items.sort(key=sort_key, reverse=(order == "desc"))
    total = len(items)
    items = items[offset : offset + limit]
    return {"total": total, "items": items}


def project_detail(db: Session, project_id: int) -> dict:
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        return None
    return {
        "id": proj.id,
        "slug": proj.slug,
        "name": proj.name or proj.slug,
        "cwd": proj.cwd,
        "first_seen_at": proj.first_seen_at,
        "last_seen_at": proj.last_seen_at,
    }


# ---------------------------------------------------------------- sessions

def session_list(db: Session, project_id: int) -> list[dict]:
    pt = PriceTable.load(db)
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.project_id == project_id)
        .order_by(SessionModel.started_at.desc())
        .all()
    )
    # 每会话按 model 的 token（一次查询）
    rows = (
        db.query(
            Message.session_id,
            Message.model,
            func.sum(Message.input_tokens),
            func.sum(Message.cache_read_tokens),
            func.sum(Message.cache_creation_tokens),
            func.sum(Message.output_tokens),
        )
        .filter(Message.project_id == project_id)
        .group_by(Message.session_id, Message.model)
        .all()
    )
    per_sess: dict[str, dict] = {}
    for sid, model, inp, cr, cc, out in rows:
        e = per_sess.setdefault(
            sid, {"tokens": {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}, "price": 0.0, "priced": False}
        )
        toks = _tokens_dict(inp, cr, cc, out)
        for f in _FIELDS:
            e["tokens"][f] += toks[f]
        cost = pt.cost(model, toks)
        if cost["priced"]:
            e["price"] += cost["total"]
            e["priced"] = True

    out = []
    for s in sessions:
        e = per_sess.get(
            s.session_id,
            {"tokens": {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}, "price": 0.0, "priced": False},
        )
        toks = e["tokens"]
        duration = None
        if s.started_at and s.ended_at:
            try:
                t0 = datetime.fromisoformat(s.started_at.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(s.ended_at.replace("Z", "+00:00"))
                duration = (t1 - t0).total_seconds()
            except ValueError:
                duration = None
        out.append(
            {
                "session_id": s.session_id,
                "title": s.title,
                "agent_name": s.agent_name,
                "version": s.version,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "duration_s": duration,
                "message_count": s.message_count,
                "subagent_count": s.subagent_count,
                "tokens": {
                    **toks,
                    "total": toks["input"] + toks["cache_read"] + toks["cache_creation"] + toks["output"],
                },
                "price": {"total": round(e["price"], 6), "priced": e["priced"], "currency": "USD"},
            }
        )
    return out


# ---------------------------------------------------------------- timeline

def timeline(db: Session, session_id: str, preview_len: int | None = None) -> dict | None:
    if preview_len is None:
        preview_len = config.PREVIEW_LEN
    session = (
        db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    )
    if not session:
        return None
    proj = db.query(Project).filter(Project.id == session.project_id).first()

    nodes = _build_file_timeline(db, session.file_path, session_id, preview_len)

    # 将子会话挂到 Agent tool_use 节点下
    subs = {
        s.tool_use_id: s
        for s in db.query(SubagentSession).filter(SubagentSession.session_id == session_id).all()
        if s.tool_use_id
    }
    for node in nodes:
        for tu in node.get("tool_uses") or []:
            sub = subs.get(tu["tool_use_id"])
            if sub is not None:
                tu["subagent"] = _build_subagent_tree(db, sub, preview_len, 0)

    # summary —— tokens/价格/message_count 由 messages 聚合（含子会话），与列表接口一致
    pt = PriceTable.load(db)
    rows = (
        db.query(
            Message.model,
            func.sum(Message.input_tokens),
            func.sum(Message.cache_read_tokens),
            func.sum(Message.cache_creation_tokens),
            func.sum(Message.output_tokens),
        )
        .filter(Message.session_id == session_id)
        .group_by(Message.model)
        .all()
    )
    toks = {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}
    price_total = 0.0
    priced = False
    for model, inp, cr, cc, out in rows:
        t = _tokens_dict(inp, cr, cc, out)
        for f in _FIELDS:
            toks[f] += t[f]
        cost = pt.cost(model, t)
        if cost["priced"]:
            price_total += cost["total"]
            priced = True
    toks["total"] = toks["input"] + toks["cache_read"] + toks["cache_creation"] + toks["output"]
    msg_count = (
        db.query(func.count(Message.id)).filter(Message.session_id == session_id).scalar() or 0
    )
    comps = (
        db.query(Compaction)
        .filter(Compaction.session_id == session_id)
        .order_by(Compaction.timestamp)
        .all()
    )
    return {
        "session_id": session.session_id,
        "project": {
            "id": proj.id if proj else None,
            "name": proj.name if proj else None,
        },
        "title": session.title,
        "agent_name": session.agent_name,
        "version": session.version,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "summary": {
            "tokens": toks,
            "price": {"total": round(price_total, 6), "priced": priced, "currency": "USD"},
            "message_count": msg_count,
            "subagent_count": session.subagent_count,
            "compactions": [
                {
                    "timestamp": c.timestamp,
                    "trigger": c.trigger,
                    "pre_tokens": c.pre_tokens,
                    "post_tokens": c.post_tokens,
                    "dropped_tokens": c.dropped_tokens,
                    "duration_ms": c.duration_ms,
                }
                for c in comps
            ],
        },
        "nodes": nodes,
    }


def _build_file_timeline(db: Session, file_path: str, session_id: str, preview_len: int) -> list[dict]:
    entries = (
        db.query(Entry)
        .filter(Entry.file_path == file_path)
        .order_by(Entry.line_no)
        .all()
    )
    row_uuids = [e.row_uuid for e in entries]
    if not row_uuids:
        return []

    msgs: dict[str, Message] = {}
    for m in db.query(Message).filter(Message.row_uuid.in_(row_uuids)).all():
        msgs[m.row_uuid] = m
    calls_by_msg: dict[str, list[ToolCall]] = {}
    for c in db.query(ToolCall).filter(ToolCall.message_row_uuid.in_(row_uuids)).all():
        calls_by_msg.setdefault(c.message_row_uuid, []).append(c)
    all_tids = [c.tool_use_id for cl in calls_by_msg.values() for c in cl]
    res_map: dict[str, ToolResult] = {}
    if all_tids:
        for r in db.query(ToolResult).filter(ToolResult.tool_use_id.in_(all_tids)).all():
            res_map[r.tool_use_id] = r

    comp_by_ts = {
        c.timestamp: c
        for c in db.query(Compaction).filter(Compaction.session_id == session_id).all()
        if c.timestamp
    }

    pt = PriceTable.load(db)
    nodes = []
    for e in entries:
        nodes.append(
            _entry_node(e, msgs.get(e.row_uuid), calls_by_msg.get(e.row_uuid, []),
                        res_map, comp_by_ts, preview_len, pt)
        )
    return nodes


def _entry_node(
    e: Entry,
    msg: Message | None,
    calls: list[ToolCall],
    res_map: dict[str, ToolResult],
    comp_by_ts: dict[str, Compaction],
    preview_len: int,
    pt: PriceTable,
) -> dict:
    if e.type == "assistant":
        node: dict = {
            "kind": "row", "type": "assistant", "row_uuid": e.row_uuid,
            "timestamp": e.timestamp, "is_user": False,
            "tokens": {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0, "total": 0},
            "price": {"total": None, "priced": False},
        }
        if msg:
            toks = {
                "input": msg.input_tokens,
                "cache_read": msg.cache_read_tokens,
                "cache_creation": msg.cache_creation_tokens,
                "output": msg.output_tokens,
                "total": msg.total_tokens,
                "thinking": msg.thinking_tokens,
            }
            node["tokens"] = toks
            node["model"] = msg.model
            node["effort"] = msg.effort
            node["stop_reason"] = msg.stop_reason
            node["price"] = pt.cost(msg.model, toks)
            content = json.loads(msg.content_json or "[]")
            texts = [b.get("text", "") for b in content if b.get("type") == "text"]
            thinks = [b.get("thinking", "") for b in content if b.get("type") == "thinking"]
            node["preview"] = _preview("\n".join(texts), preview_len)
            node["thinking_preview"] = _preview("\n".join(thinks), preview_len)

        tool_uses = []
        for c in calls:
            r = res_map.get(c.tool_use_id)
            tu = {
                "tool_use_id": c.tool_use_id,
                "name": c.tool_name,
                "skill": c.skill_name,
                "input_preview": _preview_str(c.input_json, 500),
                "result_preview": _preview_str(r.content if r else None, 1000),
                "result_error": bool(r.is_error) if r else None,
                "result_file": r.file_ref if r else None,
            }
            tool_uses.append(tu)
        node["tool_uses"] = tool_uses
        return node

    if e.type == "user":
        obj = json.loads(e.raw_json or "{}")
        node = {
            "kind": "row", "type": "user", "row_uuid": e.row_uuid,
            "timestamp": e.timestamp, "is_user": True,
            "preview": _user_preview(obj, preview_len),
            "is_compact_summary": bool(obj.get("isCompactSummary")),
        }
        return node

    if e.type == "system":
        obj = json.loads(e.raw_json or "{}")
        comp = comp_by_ts.get(e.timestamp) if e.timestamp else None
        node = {
            "kind": "row", "type": "system", "row_uuid": e.row_uuid,
            "timestamp": e.timestamp, "is_user": False,
            "subtype": obj.get("subtype"),
            "content": _preview_str(obj.get("content"), 200),
            "compaction": None,
        }
        if comp:
            node["compaction"] = {
                "trigger": comp.trigger,
                "pre_tokens": comp.pre_tokens,
                "post_tokens": comp.post_tokens,
                "dropped_tokens": comp.dropped_tokens,
                "duration_ms": comp.duration_ms,
            }
        return node

    obj = json.loads(e.raw_json or "{}")
    return {
        "kind": "row", "type": e.type, "row_uuid": e.row_uuid,
        "timestamp": e.timestamp, "is_user": False,
        "content": _preview_str(obj.get("content"), 200) if isinstance(obj.get("content"), str) else None,
    }


def _build_subagent_tree(db: Session, sub: SubagentSession, preview_len: int, depth: int) -> dict:
    node: dict = {
        "kind": "subagent",
        "agent_id": sub.agent_id,
        "agent_type": sub.agent_type,
        "description": sub.description,
        "spawn_depth": sub.spawn_depth,
        "tokens": {
            "input": sub.tokens_input,
            "cache_read": sub.tokens_cache_read,
            "cache_creation": sub.tokens_cache_creation,
            "output": sub.tokens_output,
        },
    }
    toks = node["tokens"]
    toks["total"] = toks["input"] + toks["cache_read"] + toks["cache_creation"] + toks["output"]
    node["price"] = PriceTable.load(db).cost(None, toks)
    node["message_count"] = sub.message_count

    if depth >= config.MAX_SUBAGENT_DEPTH:
        node["truncated"] = True
        node["nodes"] = []
        return node

    node["nodes"] = _build_file_timeline(db, sub.file_path, sub.session_id, preview_len)

    child_subs = {
        s.tool_use_id: s
        for s in db.query(SubagentSession)
        .filter(SubagentSession.session_id == sub.session_id)
        .all()
        if s.tool_use_id
    }
    for row in node["nodes"]:
        for tu in row.get("tool_uses") or []:
            child = child_subs.get(tu["tool_use_id"])
            if child is not None and child.id != sub.id:
                tu["subagent"] = _build_subagent_tree(db, child, preview_len, depth + 1)
    return node


def _preview(text: str | None, limit: int) -> dict:
    if not text:
        return {"text": "", "truncated": False}
    truncated = len(text) > limit
    return {"text": text[:limit], "truncated": truncated}


def _preview_str(text: str | None, limit: int) -> dict | None:
    if text is None:
        return None
    truncated = len(text) > limit
    return {"text": text[:limit], "truncated": truncated}


def _user_preview(obj: dict, preview_len: int) -> dict:
    msg = obj.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return _preview(content, preview_len)
    if isinstance(content, list):
        parts = []
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_result":
                rc = b.get("content")
                if isinstance(rc, str):
                    parts.append(rc)
                elif isinstance(rc, list):
                    parts.append(
                        " ".join(
                            x.get("text", "")
                            for x in rc
                            if isinstance(x, dict) and x.get("type") == "text"
                        )
                    )
            elif b.get("type") == "text":
                parts.append(b.get("text", ""))
        return _preview("\n".join(parts), preview_len)
    return {"text": "", "truncated": False}


# ---------------------------------------------------------------- message detail

def message_detail(db: Session, row_uuid: str, preview_len: int | None = None) -> dict | None:
    if preview_len is None:
        preview_len = config.PREVIEW_LEN
    e = db.query(Entry).filter(Entry.row_uuid == row_uuid).first()
    if not e:
        return None
    obj = json.loads(e.raw_json or "{}")
    msg = db.query(Message).filter(Message.row_uuid == row_uuid).first()
    pt = PriceTable.load(db)

    detail: dict = {
        "row_uuid": row_uuid,
        "type": e.type,
        "timestamp": e.timestamp,
        "raw": obj,
    }

    if msg:
        detail["message_id"] = msg.message_id
        detail["model"] = msg.model
        detail["effort"] = msg.effort
        detail["stop_reason"] = msg.stop_reason
        detail["tokens"] = {
            "input": msg.input_tokens,
            "cache_read": msg.cache_read_tokens,
            "cache_creation": msg.cache_creation_tokens,
            "output": msg.output_tokens,
            "thinking": msg.thinking_tokens,
            "total": msg.total_tokens,
        }
        detail["price"] = pt.cost(msg.model, detail["tokens"])
        try:
            detail["content"] = json.loads(msg.content_json or "[]")
        except json.JSONDecodeError:
            detail["content"] = []

        calls = (
            db.query(ToolCall)
            .filter(ToolCall.message_row_uuid == row_uuid)
            .order_by(ToolCall.id)
            .all()
        )
        tids = [c.tool_use_id for c in calls]
        res_map: dict[str, ToolResult] = {}
        if tids:
            for r in db.query(ToolResult).filter(ToolResult.tool_use_id.in_(tids)).all():
                res_map[r.tool_use_id] = r
        detail["tool_calls"] = []
        for c in calls:
            r = res_map.get(c.tool_use_id)
            entry = {
                "tool_use_id": c.tool_use_id,
                "name": c.tool_name,
                "skill": c.skill_name,
                "input": _safe_json_loads(c.input_json) or {},
                "result": _safe_json_loads(r.content) if r else None,
                "result_error": bool(r.is_error) if r else None,
                "result_file": r.file_ref if r else None,
            }
            if r and r.file_ref:
                entry["result_file_content"] = _read_result_file(db, r.file_ref, e.project_id)
            detail["tool_calls"].append(entry)

        # 子会话引用
        subs = (
            db.query(SubagentSession)
            .filter(
                SubagentSession.session_id == msg.session_id,
                SubagentSession.tool_use_id.in_(tids) if tids else False,
            )
            .all()
        )
        detail["subagents"] = [
            {
                "agent_id": s.agent_id,
                "agent_type": s.agent_type,
                "description": s.description,
                "spawn_depth": s.spawn_depth,
            }
            for s in subs
        ]
    return detail


def _read_result_file(db: Session, file_ref: str, project_id: int | None) -> dict:
    p = Path(file_ref)
    if not p.is_absolute():
        proj = db.query(Project).filter(Project.id == project_id).first() if project_id else None
        if proj:
            cand = config.CLAUDE_PROJECTS_DIR / proj.slug / p
            if cand.exists():
                p = cand
    if not p.exists() or not p.is_file():
        return {"error": "file not found", "path": file_ref}
    try:
        data = p.read_text(encoding="utf-8", errors="replace")
        truncated = len(data) > config.TOOL_RESULT_FILE_LIMIT
        return {
            "content": data[: config.TOOL_RESULT_FILE_LIMIT],
            "truncated": truncated,
            "path": str(p),
        }
    except OSError:
        return {"error": "read failed", "path": str(p)}
