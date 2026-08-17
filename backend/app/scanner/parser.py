"""单文件 JSONL 解析。不直接写库，返回结构化 ParseResult 由 pipeline 批量入库。

关键规则：
- usage 只存在于 assistant 行的 message.usage —— 一次 assistant 行 = 一次 API 往返。
- 归属链 rollup_bucket：Skill 往返更新桶，Agent 及其后往返继承；无链者归 <工具名> 或 <text>。
- tool_result 单独入库（tool_results），供详情直取。
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import config

IGNORED_TYPES = {"file-history-snapshot", "file-history-delta"}

_LOCAL_TZ: ZoneInfo | None = None


def _local_tz() -> ZoneInfo:
    global _LOCAL_TZ
    if _LOCAL_TZ is None:
        if config.TZ_NAME == "local":
            _LOCAL_TZ = datetime.now().astimezone().tzinfo
        else:
            _LOCAL_TZ = ZoneInfo(config.TZ_NAME)
    return _LOCAL_TZ


def to_day_local(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_local_tz()).strftime("%Y-%m-%d")
    except ValueError:
        return None


@dataclass
class ParseResult:
    row_uuids: set[str] = field(default_factory=set)
    entries: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    compactions: list[dict] = field(default_factory=list)
    session_id: str | None = None
    cwd: str | None = None
    version: str | None = None
    title: str | None = None
    agent_name: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    message_count: int = 0
    tokens: dict = field(
        default_factory=lambda: {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}
    )
    skill_names: set[str] = field(default_factory=set)
    bucket: str | None = None  # 当前归属桶（会话内可变状态）


def parse_file(
    file_path: Path,
    project_id: int,
    *,
    agent_id: str | None = None,
    kind: str = "main",
    seed_bucket: str | None = None,
) -> ParseResult:
    res = ParseResult()
    res.bucket = seed_bucket
    file_path_str = str(file_path)

    with open(file_path, "rb") as f:
        for line_no, raw in enumerate(f):
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            _process_line(
                res, obj, line_no, file_path_str, project_id, agent_id, kind
            )
    return res


def _process_line(
    res: ParseResult,
    obj: dict,
    line_no: int,
    file_path_str: str,
    project_id: int,
    agent_id: str | None,
    kind: str,
) -> None:
    otype = obj.get("type")
    if otype in IGNORED_TYPES:
        return

    row_uuid = obj.get("uuid")
    if not row_uuid:
        row_uuid = f"{file_path_str}:{line_no}:{otype}"  # 罕见兜底

    res.row_uuids.add(row_uuid)
    parent_uuid = obj.get("parentUuid")
    timestamp = obj.get("timestamp")
    session_id = obj.get("sessionId") or obj.get("session_id")
    cwd = obj.get("cwd")
    version = obj.get("version")
    is_sidechain = 1 if obj.get("isSidechain") else 0

    if session_id:
        res.session_id = session_id
    if cwd:
        res.cwd = cwd
    if version:
        res.version = version
    if timestamp:
        if res.started_at is None:
            res.started_at = timestamp
        res.ended_at = timestamp

    tool_use_id: str | None = None
    has_message = 0

    if otype == "assistant":
        message = obj.get("message") or {}
        if message.get("id"):
            has_message = 1
            _process_message(
                res, obj, message, row_uuid, timestamp, session_id,
                project_id, agent_id, kind, is_sidechain,
            )
        for block in message.get("content") or []:
            if block.get("type") == "tool_use":
                tool_use_id = block.get("id")
                break
    elif otype == "user":
        msg = obj.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    tid = block.get("tool_use_id")
                    if tid:
                        if tool_use_id is None:
                            tool_use_id = tid
                        _process_tool_result(
                            res, tid, block, row_uuid, timestamp, session_id, project_id
                        )
    elif otype == "system":
        if obj.get("subtype") == "compact_boundary":
            meta = obj.get("compactMetadata") or {}
            res.compactions.append(
                {
                    "row_uuid": obj.get("uuid"),
                    "session_id": session_id,
                    "project_id": project_id,
                    "timestamp": timestamp,
                    "trigger": meta.get("trigger"),
                    "pre_tokens": meta.get("preTokens", 0),
                    "post_tokens": meta.get("postTokens", 0),
                    "dropped_tokens": meta.get("cumulativeDroppedTokens", 0),
                    "duration_ms": meta.get("durationMs", 0),
                }
            )
    elif otype == "ai-title":
        res.title = obj.get("aiTitle") or res.title
    elif otype == "agent-name":
        res.agent_name = obj.get("agentName") or res.agent_name

    res.entries.append(
        {
            "row_uuid": row_uuid,
            "parent_uuid": parent_uuid,
            "type": otype,
            "session_id": session_id,
            "agent_id": agent_id,
            "project_id": project_id,
            "timestamp": timestamp,
            "file_path": file_path_str,
            "line_no": line_no,
            "tool_use_id": tool_use_id,
            "has_message": has_message,
            "raw_json": json.dumps(obj, ensure_ascii=False),
        }
    )


def _process_message(
    res: ParseResult,
    obj: dict,
    message: dict,
    row_uuid: str,
    timestamp: str | None,
    session_id: str | None,
    project_id: int,
    agent_id: str | None,
    kind: str,
    is_sidechain: int,
) -> None:
    usage = message.get("usage") or {}
    cc_extra = usage.get("cache_creation") or {}
    cc = int(usage.get("cache_creation_input_tokens", 0) or 0)
    cc += int(cc_extra.get("ephemeral_5m_input_tokens", 0) or 0)
    cc += int(cc_extra.get("ephemeral_1h_input_tokens", 0) or 0)
    inp = int(usage.get("input_tokens", 0) or 0)
    cr = int(usage.get("cache_read_input_tokens", 0) or 0)
    out = int(usage.get("output_tokens", 0) or 0)
    think = int((usage.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0)
    total = inp + cr + cc + out

    model = message.get("model")
    content = message.get("content") or []
    primary_tool: str | None = None
    tool_uses: list[dict] = []
    for block in content:
        if block.get("type") == "tool_use":
            if primary_tool is None:
                primary_tool = block.get("name")
            tool_uses.append(block)

    skill: str | None = None
    if primary_tool == "Skill" and tool_uses:
        skill = (tool_uses[0].get("input") or {}).get("skill")

    if primary_tool == "Skill" and skill:
        res.bucket = skill
    bucket = res.bucket if res.bucket else (f"<{primary_tool}>" if primary_tool else "<text>")

    res.messages.append(
        {
            "row_uuid": row_uuid,
            "message_id": message.get("id"),
            "kind": kind,
            "session_id": session_id or res.session_id,
            "agent_id": agent_id,
            "project_id": project_id,
            "model": model,
            "timestamp": timestamp,
            "day_local": to_day_local(timestamp),
            "is_sidechain": is_sidechain,
            "input_tokens": inp,
            "cache_read_tokens": cr,
            "cache_creation_tokens": cc,
            "output_tokens": out,
            "thinking_tokens": think,
            "total_tokens": total,
            "content_json": json.dumps(content, ensure_ascii=False),
            "stop_reason": message.get("stop_reason"),
            "effort": obj.get("effort"),
            "primary_tool": primary_tool,
            "rollup_bucket": bucket,
        }
    )
    res.message_count += 1
    res.tokens["input"] += inp
    res.tokens["cache_read"] += cr
    res.tokens["cache_creation"] += cc
    res.tokens["output"] += out

    for tu in tool_uses:
        input_dict = tu.get("input") or {}
        sk: str | None = None
        if tu.get("name") == "Skill":
            sk = input_dict.get("skill")
            if sk:
                res.skill_names.add(sk)
        res.tool_calls.append(
            {
                "tool_use_id": tu.get("id"),
                "message_row_uuid": row_uuid,
                "session_id": session_id or res.session_id,
                "agent_id": agent_id,
                "project_id": project_id,
                "tool_name": tu.get("name"),
                "skill_name": sk,
                "input_json": json.dumps(input_dict, ensure_ascii=False),
                "created_at": timestamp,
            }
        )


def _process_tool_result(
    res: ParseResult,
    tool_use_id: str,
    block: dict,
    entry_row_uuid: str,
    timestamp: str | None,
    session_id: str | None,
    project_id: int,
) -> None:
    res_content = block.get("content")
    is_error = 1 if block.get("is_error") else 0
    file_ref: str | None = None

    if isinstance(res_content, str):
        m = re.search(r"(?P<path>[^\"\s]*[tT]ool-results[\\/][^\"\s]*)", res_content)
        if m:
            file_ref = m.group("path")
        elif "tool-results" in res_content:
            stripped = res_content.strip()
            if stripped.endswith(".txt"):
                file_ref = stripped

    if isinstance(res_content, str):
        content_str = res_content
    elif res_content is None:
        content_str = ""
    else:
        content_str = json.dumps(res_content, ensure_ascii=False)

    res.tool_results.append(
        {
            "tool_use_id": tool_use_id,
            "content": content_str,
            "is_error": is_error,
            "file_ref": file_ref,
            "entry_row_uuid": entry_row_uuid,
            "timestamp": timestamp,
        }
    )
