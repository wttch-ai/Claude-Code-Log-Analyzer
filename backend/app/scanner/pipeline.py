"""扫描编排：指纹增量跳过、批量入库去重、过期清理、子会话两遍关联、汇总。

流程：discover → 确保 projects → 第 1 遍主文件 → 第 2 遍子文件(spawnDepth 序) → finalize。
"""

import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .. import config
from ..db import SessionLocal
from ..models import (
    Compaction,
    Entry,
    FileMeta,
    Message,
    Project,
    ScanRun,
    Session as SessionModel,
    SubagentSession,
    ToolCall,
    ToolResult,
)
from . import discover
from .linkage import agent_id_from_path, find_parent_bucket, load_meta, spawn_depth
from .parser import parse_file

_BATCH = 500
_scan_lock = threading.Lock()
_scanning: list[int] = []


def is_scanning() -> bool:
    return bool(_scanning)


def latest_scan(db: Session) -> ScanRun | None:
    return db.query(ScanRun).order_by(ScanRun.id.desc()).first()


def run_scan(mode: str = "incremental") -> ScanRun:
    """触发扫描（阻塞）。串行化，防止并发。"""
    with _scan_lock:
        db = SessionLocal()
        run = ScanRun(mode=mode)
        db.add(run)
        db.commit()
        db.refresh(run)
        _scanning.append(run.id)
        try:
            _scan_impl(db, run)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}"
        finally:
            run.finished_at = datetime.now().isoformat(timespec="seconds")
            db.commit()
            _scanning.remove(run.id)
            db.close()
        return run


# ---------------------------------------------------------------- 内部实现

def _scan_impl(db: Session, run: ScanRun) -> None:
    projects_dir = config.CLAUDE_PROJECTS_DIR
    project_files = discover.discover(projects_dir)
    run.projects_found = len(project_files)
    run.main_files = sum(len(p.main_files) for p in project_files)
    run.subagent_files = sum(len(p.subagent_files) for p in project_files)
    db.commit()

    # 1) 确保 project 行
    proj_ids: dict[str, int] = {}
    for pf in project_files:
        proj = db.query(Project).filter(Project.slug == pf.slug).first()
        if not proj:
            proj = Project(
                slug=pf.slug,
                name=pf.slug,
                first_seen_at=datetime.now().isoformat(timespec="seconds"),
            )
            db.add(proj)
            db.flush()
        proj_ids[pf.slug] = proj.id
    db.commit()

    # 2) 第 1 遍：主文件
    for pf in project_files:
        proj = db.query(Project).filter(Project.id == proj_ids[pf.slug]).one()
        for mf in pf.main_files:
            _process_main_file(db, run, mf, proj)
            db.commit()

    # 3) 第 2 遍：子文件按 spawnDepth 升序
    sub_paths: list[tuple[int, Path, str]] = []
    for pf in project_files:
        for sf in pf.subagent_files:
            meta = load_meta(sf)
            sub_paths.append((spawn_depth(meta), sf, pf.slug))
    for _depth, sf, slug in sorted(sub_paths, key=lambda t: t[0]):
        proj = db.query(Project).filter(Project.id == proj_ids.get(slug, -1)).first()
        if proj is None:
            continue
        _process_subagent_file(db, run, sf, proj)
        db.commit()

    # 4) finalize：subagent_count、已删除文件清理
    _finalize(db, run, projects_dir)
    run.status = "done"


# ---------------------------------------------------------------- 文件处理

def _process_main_file(db: Session, run: ScanRun, mf: Path, proj: Project) -> None:
    if _skip_unchanged(db, run, mf):
        return
    result = parse_file(mf, proj.id, kind="main")

    if result.cwd and not proj.cwd:
        proj.cwd = result.cwd
        proj.name = Path(result.cwd).name or proj.slug
    if result.ended_at:
        proj.last_seen_at = result.ended_at

    run.new_entries += _ingest_file(db, result, mf)
    _upsert_session(db, result, proj.id, mf)
    _update_file_meta(db, mf)
    run.updated_files += 1
    run.entries_found += len(result.entries)


def _process_subagent_file(db: Session, run: ScanRun, sf: Path, proj: Project) -> None:
    if _skip_unchanged(db, run, sf):
        return
    meta = load_meta(sf)
    agent_id = agent_id_from_path(sf)
    tool_use_id = meta.get("toolUseId")
    seed_bucket = find_parent_bucket(db, tool_use_id)
    result = parse_file(
        sf, proj.id, agent_id=agent_id, kind="subagent", seed_bucket=seed_bucket
    )

    if tool_use_id:
        db.query(ToolCall).filter(ToolCall.tool_use_id == tool_use_id).update(
            {"subagent_ref": agent_id}
        )

    run.new_entries += _ingest_file(db, result, sf)
    _upsert_subagent(db, result, meta, proj.id, sf, agent_id)
    _update_file_meta(db, sf)
    run.updated_files += 1
    run.entries_found += len(result.entries)


# ---------------------------------------------------------------- 工具函数

def _skip_unchanged(db: Session, run: ScanRun, path: Path) -> bool:
    st = path.stat()
    fm = db.query(FileMeta).filter(FileMeta.path == str(path)).first()
    if (
        run.mode != "full"
        and fm is not None
        and fm.size_bytes == st.st_size
        and abs(fm.mtime - st.st_mtime) < 1e-6
    ):
        run.unchanged_files += 1
        return True
    return False


def _ingest_file(db: Session, result, path: Path) -> int:
    """批量入库（INSERT OR IGNORE）+ 过期行清理，返回新增行数。"""
    file_path = str(path)

    existing = db.query(Entry.row_uuid).filter(Entry.file_path == file_path).all()
    existing_set = {r[0] for r in existing}
    new_count = len(result.row_uuids - existing_set)

    _bulk_ignore(db, Entry.__table__, result.entries, ["row_uuid"])
    _bulk_ignore(db, Message.__table__, result.messages, ["row_uuid"])
    _bulk_ignore(db, ToolCall.__table__, result.tool_calls, ["tool_use_id"])
    _bulk_ignore(db, ToolResult.__table__, result.tool_results, ["tool_use_id"])
    _bulk_ignore(db, Compaction.__table__, result.compactions, ["row_uuid"])

    removed = existing_set - result.row_uuids
    if removed:
        removed_list = list(removed)
        db.execute(delete(ToolCall).where(ToolCall.message_row_uuid.in_(removed_list)))
        db.execute(delete(ToolResult).where(ToolResult.entry_row_uuid.in_(removed_list)))
        db.execute(delete(Message).where(Message.row_uuid.in_(removed_list)))
        db.execute(
            delete(Entry).where(
                Entry.file_path == file_path, Entry.row_uuid.in_(removed_list)
            )
        )
    return new_count


def _bulk_ignore(db: Session, table, rows: list[dict], index_elements: list[str]) -> None:
    for i in range(0, len(rows), _BATCH):
        chunk = rows[i : i + _BATCH]
        if not chunk:
            continue
        stmt = sqlite_insert(table).values(chunk).on_conflict_do_nothing(
            index_elements=index_elements
        )
        db.execute(stmt)


def _upsert_session(db: Session, result, project_id: int, file_path: Path) -> None:
    session_id = result.session_id
    if not session_id:
        return
    s = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if s is None:
        s = SessionModel(
            session_id=session_id, project_id=project_id, file_path=str(file_path)
        )
        db.add(s)
        db.flush()
    if result.title:
        s.title = result.title
    if result.agent_name:
        s.agent_name = result.agent_name
    if result.version:
        s.version = result.version
    s.started_at = result.started_at or s.started_at
    s.ended_at = result.ended_at or s.ended_at
    s.message_count = result.message_count
    s.tokens_input = result.tokens["input"]
    s.tokens_cache_read = result.tokens["cache_read"]
    s.tokens_cache_creation = result.tokens["cache_creation"]
    s.tokens_output = result.tokens["output"]


def _upsert_subagent(
    db: Session, result, meta: dict, project_id: int, file_path: Path, agent_id: str
) -> None:
    session_id = result.session_id
    if not session_id:
        return
    s = (
        db.query(SubagentSession)
        .filter(
            SubagentSession.session_id == session_id,
            SubagentSession.agent_id == agent_id,
        )
        .first()
    )
    if s is None:
        s = SubagentSession(
            session_id=session_id, agent_id=agent_id, file_path=str(file_path)
        )
        db.add(s)
        db.flush()
    s.agent_type = meta.get("agentType")
    s.description = meta.get("description")
    s.tool_use_id = meta.get("toolUseId")
    s.spawn_depth = spawn_depth(meta)
    s.started_at = result.started_at or s.started_at
    s.ended_at = result.ended_at or s.ended_at
    s.message_count = result.message_count
    s.tokens_input = result.tokens["input"]
    s.tokens_cache_read = result.tokens["cache_read"]
    s.tokens_cache_creation = result.tokens["cache_creation"]
    s.tokens_output = result.tokens["output"]


def _update_file_meta(db: Session, path: Path) -> None:
    st = path.stat()
    fm = db.query(FileMeta).filter(FileMeta.path == str(path)).first()
    if fm is None:
        fm = FileMeta(path=str(path))
        db.add(fm)
    fm.size_bytes = st.st_size
    fm.mtime = st.st_mtime
    fm.status = "parsed"
    fm.first_pass_done = 1
    fm.last_parsed_at = datetime.now().isoformat(timespec="seconds")


def _finalize(db: Session, run: ScanRun, projects_dir: Path) -> None:
    # subagent_count 回填
    distinct_sids = db.query(SubagentSession.session_id).distinct().all()
    for (sid,) in distinct_sids:
        cnt = db.query(SubagentSession).filter(SubagentSession.session_id == sid).count()
        db.query(SessionModel).filter(SessionModel.session_id == sid).update(
            {"subagent_count": cnt}
        )

    # 已删除文件的库数据清理
    known: set[str] = set()
    for pf in discover.discover(projects_dir):
        known.update(str(f) for f in pf.main_files)
        known.update(str(f) for f in pf.subagent_files)
    for fm in db.query(FileMeta).all():
        if fm.path not in known:
            _purge_file_data(db, fm.path)
            db.delete(fm)


def _purge_file_data(db: Session, file_path: str) -> None:
    """删除某文件已不再存在的全部库数据（entries/messages/tool_calls/tool_results）。"""
    uuids = [r for (r,) in db.query(Entry.row_uuid).filter(Entry.file_path == file_path).all()]
    if uuids:
        db.execute(delete(ToolCall).where(ToolCall.message_row_uuid.in_(uuids)))
        db.execute(delete(ToolResult).where(ToolResult.entry_row_uuid.in_(uuids)))
        db.execute(delete(Message).where(Message.row_uuid.in_(uuids)))
        db.execute(delete(Entry).where(Entry.file_path == file_path))
