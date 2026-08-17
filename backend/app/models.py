"""全部 SQLite 表的 SQLAlchemy 2.0 声明式定义。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

_TIMESTAMP = lambda: datetime.now().isoformat(timespec="seconds")  # noqa: E731


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    cwd: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(String(255))
    first_seen_at: Mapped[str | None] = mapped_column(String(32))
    last_seen_at: Mapped[str | None] = mapped_column(String(32))


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    agent_name: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[str | None] = mapped_column(String(64))
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(String(32))
    ended_at: Mapped[str | None] = mapped_column(String(32))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    subagent_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens_input: Mapped[int] = mapped_column(BigInteger, default=0)
    tokens_cache_read: Mapped[int] = mapped_column(BigInteger, default=0)
    tokens_cache_creation: Mapped[int] = mapped_column(BigInteger, default=0)
    tokens_output: Mapped[int] = mapped_column(BigInteger, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session {self.session_id} project={self.project_id}>"


class SubagentSession(Base):
    __tablename__ = "subagent_sessions"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_type: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    tool_use_id: Mapped[str | None] = mapped_column(String(128))
    spawn_depth: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(String(32))
    ended_at: Mapped[str | None] = mapped_column(String(32))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens_input: Mapped[int] = mapped_column(BigInteger, default=0)
    tokens_cache_read: Mapped[int] = mapped_column(BigInteger, default=0)
    tokens_cache_creation: Mapped[int] = mapped_column(BigInteger, default=0)
    tokens_output: Mapped[int] = mapped_column(BigInteger, default=0)


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    row_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    parent_uuid: Mapped[str | None] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64))
    agent_id: Mapped[str | None] = mapped_column(String(64))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    timestamp: Mapped[str | None] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, default=0)
    tool_use_id: Mapped[str | None] = mapped_column(String(128), index=True)
    has_message: Mapped[int] = mapped_column(Integer, default=0)
    raw_json: Mapped[str | None] = mapped_column(Text)


class Message(Base):
    """一次 assistant API 往返。token 唯一来源。"""

    __tablename__ = "messages"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    row_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    message_id: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # main | subagent
    session_id: Mapped[str | None] = mapped_column(String(64))
    agent_id: Mapped[str | None] = mapped_column(String(64))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), index=True)
    timestamp: Mapped[str | None] = mapped_column(String(32))
    day_local: Mapped[str | None] = mapped_column(String(10), index=True)
    is_sidechain: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    thinking_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    content_json: Mapped[str | None] = mapped_column(Text)
    stop_reason: Mapped[str | None] = mapped_column(String(64))
    effort: Mapped[str | None] = mapped_column(String(32))
    primary_tool: Mapped[str | None] = mapped_column(String(64))
    rollup_bucket: Mapped[str | None] = mapped_column(String(128), index=True)


class ToolCall(Base):
    __tablename__ = "tool_calls"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool_use_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    message_row_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    skill_name: Mapped[str | None] = mapped_column(String(128), index=True)
    input_json: Mapped[str | None] = mapped_column(Text)
    subagent_ref: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[str | None] = mapped_column(String(32))


class ToolResult(Base):
    """tool_use_id 对应的工具输出（来自其后 user 行的 tool_result 块）。"""

    __tablename__ = "tool_results"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool_use_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    content: Mapped[str | None] = mapped_column(Text)  # content 序列化（str 或块列表）
    is_error: Mapped[int] = mapped_column(Integer, default=0)
    file_ref: Mapped[str | None] = mapped_column(Text)  # 落盘引用路径（tool-results/*.txt）
    entry_row_uuid: Mapped[str | None] = mapped_column(String(64))
    timestamp: Mapped[str | None] = mapped_column(String(32))


class Compaction(Base):
    __tablename__ = "compactions"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    row_uuid: Mapped[str | None] = mapped_column(String(64), unique=True)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    timestamp: Mapped[str | None] = mapped_column(String(32))
    trigger: Mapped[str | None] = mapped_column(String(32))
    pre_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    post_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    dropped_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class FileMeta(Base):
    __tablename__ = "files_meta"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    mtime: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    parsed_line: Mapped[int] = mapped_column(Integer, default=0)
    first_pass_done: Mapped[int] = mapped_column(Integer, default=0)
    last_parsed_at: Mapped[str | None] = mapped_column(String(32))


class ModelPrice(Base):
    __tablename__ = "model_prices"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    input_price: Mapped[float] = mapped_column(Float, default=0)
    cache_read_price: Mapped[float] = mapped_column(Float, default=0)
    cache_creation_price: Mapped[float] = mapped_column(Float, default=0)
    output_price: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    note: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[str | None] = mapped_column(String(32))


class ScanRun(Base):
    __tablename__ = "scan_runs"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), default="incremental")
    status: Mapped[str] = mapped_column(String(16), default="running")
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(String(32), default=_now_iso)
    finished_at: Mapped[str | None] = mapped_column(String(32))
    projects_found: Mapped[int] = mapped_column(Integer, default=0)
    main_files: Mapped[int] = mapped_column(Integer, default=0)
    subagent_files: Mapped[int] = mapped_column(Integer, default=0)
    entries_found: Mapped[int] = mapped_column(Integer, default=0)
    new_entries: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_files: Mapped[int] = mapped_column(Integer, default=0)
    updated_files: Mapped[int] = mapped_column(Integer, default=0)
