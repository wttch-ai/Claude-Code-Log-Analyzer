"""子 agent 会话关联：meta.toolUseId → 父 Agent 调用 → 归属桶。

子 agent 的 usage 只存在于其自身 subagents/agent-<id>.jsonl，
主文件 Agent 工具行无 usage。故子会话成本 = 其文件 assistant 行 usage 求和。
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Message, ToolCall


def agent_id_from_path(agent_jsonl: Path) -> str:
    """agent-<id>.jsonl → <id>"""
    name = agent_jsonl.name
    return name[len("agent-") : -len(".jsonl")]


def load_meta(agent_jsonl: Path) -> dict:
    """agent-<id>.jsonl → agent-<id>.meta.json；读取失败返回 {}。"""
    meta_path = agent_jsonl.with_name(
        agent_jsonl.name.replace(".jsonl", ".meta.json")
    )
    if not meta_path.exists():
        return {}
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def spawn_depth(meta: dict) -> int:
    try:
        return int(meta.get("spawnDepth", 0) or 0)
    except (TypeError, ValueError):
        return 0


def find_parent_bucket(db: Session, tool_use_id: str | None) -> str | None:
    """父 Agent 调用所在消息的 rollup_bucket，作为子会话的初始归属桶。"""
    if not tool_use_id:
        return None
    row = (
        db.query(Message.rollup_bucket)
        .join(ToolCall, ToolCall.message_row_uuid == Message.row_uuid)
        .filter(ToolCall.tool_use_id == tool_use_id, ToolCall.tool_name == "Agent")
        .first()
    )
    return row[0] if row else None
