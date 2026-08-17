"""命令行扫描工具。

用法（cd backend 后）：
    .venv/Scripts/python -m scripts.scan_cli [--mode full|incremental]
"""

import argparse
import time

from app.db import init_db
from app.scanner.pipeline import run_scan


def main() -> None:
    ap = argparse.ArgumentParser(description="扫描 Claude Code 日志")
    ap.add_argument("--mode", default="incremental", choices=["incremental", "full"])
    args = ap.parse_args()

    init_db()
    t0 = time.time()
    run = run_scan(args.mode)
    dt = time.time() - t0
    print(f"mode={run.mode} status={run.status} elapsed={dt:.1f}s")
    print(
        f"projects={run.projects_found} main={run.main_files} sub={run.subagent_files}"
    )
    print(
        f"entries_found={run.entries_found} new_entries={run.new_entries} "
        f"updated_files={run.updated_files} unchanged_files={run.unchanged_files}"
    )
    if run.error:
        print("ERROR:", run.error)


if __name__ == "__main__":
    main()
