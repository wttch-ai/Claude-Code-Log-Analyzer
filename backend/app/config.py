"""全局配置。"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "analyzer.db"

# Claude Code 日志根目录（可用环境变量 CLAUDE_PROJECTS_DIR 覆盖）
CLAUDE_PROJECTS_DIR = Path(
    __import__("os").environ.get(
        "CLAUDE_PROJECTS_DIR", r"C:\Users\Administrator\.claude\projects"
    )
)

# 本地时区名称。仅用于 day_local 聚合键；"local" = 系统时区。
TZ_NAME = "local"

# 启动时是否后台自动增量扫描
SCAN_ON_STARTUP = True

# 定时自动增量扫描间隔（秒，可用环境变量 AUTO_SCAN_INTERVAL_S 覆盖；0 = 关闭）
AUTO_SCAN_INTERVAL_S = int(
    __import__("os").environ.get("AUTO_SCAN_INTERVAL_S", "3600")
)

# 时间轴预览截断长度
PREVIEW_LEN = 2000
# 详情接口读取 tool-results 落盘文件上限
TOOL_RESULT_FILE_LIMIT = 1024 * 1024  # 1 MB
# 子会话嵌套深度上限
MAX_SUBAGENT_DEPTH = 10
