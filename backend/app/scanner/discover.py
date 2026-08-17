"""文件发现：扫描 Claude 日志根目录，分出主会话与子 agent 会话文件。"""

import re
from dataclasses import dataclass, field
from pathlib import Path

# 主会话文件名：sessionId-UUID.jsonl
_MAIN_RE = re.compile(r"^[0-9a-fA-F-]{36}\.jsonl$")
# 子 agent 文件：agent-<id>.jsonl / agent-<id>.meta.json
_AGENT_JSONL_RE = re.compile(r"^agent-(.+)\.jsonl$")
_AGENT_META_RE = re.compile(r"^agent-(.+)\.meta\.json$")


@dataclass
class ProjectFiles:
    slug: str
    directory: Path
    main_files: list[Path] = field(default_factory=list)
    subagent_files: list[Path] = field(default_factory=list)


def _extract_agent_id(filename: str) -> str | None:
    m = _AGENT_JSONL_RE.match(filename)
    return m.group(1) if m else None


def discover(projects_dir: Path) -> list[ProjectFiles]:
    """返回排序后的项目文件清单。仅读取目录结构，不解析文件内容。"""
    if not projects_dir.is_dir():
        raise FileNotFoundError(f"日志根目录不存在: {projects_dir}")

    result: list[ProjectFiles] = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        slug = project_dir.name
        pf = ProjectFiles(slug=slug, directory=project_dir)

        for item in sorted(project_dir.iterdir()):
            if item.is_file() and _MAIN_RE.match(item.name):
                pf.main_files.append(item)
            elif item.is_dir():
                subagents = item / "subagents"
                if subagents.is_dir():
                    for g in sorted(subagents.iterdir()):
                        if g.is_file() and _extract_agent_id(g.name):
                            pf.subagent_files.append(g)
        result.append(pf)

    return result


def main_file_to_session_id(path: Path) -> str | None:
    """从主文件名提取 sessionId（= 去 .jsonl 后的 UUID）。"""
    return path.stem if path.name.endswith(".jsonl") else None
