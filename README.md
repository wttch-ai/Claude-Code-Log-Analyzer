# Claude Code 日志分析系统

解析 Claude Code 本地会话日志（`~/.claude/projects`），全量入库 SQLite，增量去重扫描；以 Vue 前端图表展示 token 消耗——按 **skill / project / session / model** 维度定位「吃 token 之处」，并下钻至对话时间轴，逐条查看消息的输入输出、tool 调用、skill 调用与 subagent 明细。

## 功能

- **全量 / 增量扫描**：首次全量解析全部 jsonl；之后按 `mtime+size` 指纹跳过未变文件，`row_uuid` 主键去重，重解析后清理过期行。
- **token 归因**：Skill → 其后续 Agent 及子会话全部往返，一并归入该 skill 桶（`rollup_bucket`），保证每个 token 可归桶。
- **子会话嵌套**：subagent 挂在主时间轴 Agent tool_use 节点下，支持多级递归；统计含子会话，未丢失。
- **多维堆叠图**：按天 × project / skill / tool / model；>12 系列自动并入 Other。
- **对话时间轴**：按天分组，TokenBar 四档堆叠（input / cache_read / cache_creation / output），>200k 告警、>1M 红标；上下文压缩（compact_boundary）标记 pre→post 与丢弃 token。
- **消息详情抽屉**：回复文本 / 思考 / 工具输入输出（含 tool-results 落盘文件按需读取）/ 用量明细 / 子会话引用。
- **价格可配置**：按 model 单价（USD / 1M tokens），精确匹配 → `*` 兜底；全局切换 token 数量或预估价格显示（前端不重取数）。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python + FastAPI + SQLAlchemy 2.0 + SQLite（WAL） |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts |

## 目录结构

```
backend/
  app/
    config.py            # CLAUDE_PROJECTS_DIR / DB_PATH / 时区等
    db.py                # engine + WAL pragmas
    models.py            # 全表模型
    main.py              # FastAPI 入口（lifespan 启动增量扫描）
    scanner/             # discover → parser → pipeline → linkage（增量 + 归属链 + 子会话关联）
    services/            # pricing（价格计算）、stats（聚合 / 时间轴 / 详情）
    api/                 # scan / overview / aggregate / projects / sessions / prices
  scripts/
    scan_cli.py          # 命令行触发扫描
    seed_prices.py       # 写入默认价格
    smoke_test.py        # API smoke test
  requirements.txt
frontend/
  src/
    views/               # Overview / Projects / ProjectDetail / SessionDetail / Prices / Scan
    components/          # 图表、时间轴、TokenBar、CompactionMarker、详情抽屉等
    stores/              # display（tokens|price 模式）、scan（轮询）
    api/ types/ utils/   # HTTP、类型、格式化/配色
```

## 快速开始

要求：Python 3.10+，Node 18+。

```bash
# ---- 后端 ----
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt        # Windows
.venv/Scripts/python -m scripts.seed_prices          # 写入默认价格
.venv/Scripts/python -m uvicorn app.main:app --reload
# 服务 http://127.0.0.1:8000 ，启动时后台自动跑一次增量扫描

# ---- 前端（另开终端） ----
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

首次入库也可手动触发全量扫描：`POST /api/scan?mode=full`（或在「扫描」页点击）。

### 配置

默认读取 `C:\Users\Administrator\.claude\projects`，可用环境变量覆盖：

```
set CLAUDE_PROJECTS_DIR=D:\path\to\projects
set CLAUDE_LOG_DB=E:\path\to\analyzer.db
```

## 日志格式要点

- 主会话 `projects/<cwd编码>/<sessionId>.jsonl`；子会话 `<sessionId>/subagents/agent-<id>.jsonl` + `.meta.json`；超大输出落盘 `tool-results/*.txt`。
- `usage` 仅存于 `assistant` 行 `message.usage`（input / cache_read / cache_creation / output / thinking）。一行 assistant = 一次 API 往返。
- 行 `uuid` 全局唯一（去重键）；`parentUuid` 指文件内上一行。
- 压缩事件：`system subtype=compact_boundary` 携带 `compactMetadata`（pre/post/cumulativeDroppedTokens）。

## 数据模型

`projects / sessions / subagent_sessions / entries / messages / tool_calls / tool_results / compactions / files_meta / model_prices / scan_runs`。

`files_meta` 为增量指纹；`messages` 存四档 tokens + thinking + `rollup_bucket`（skill 归因桶）；`entries` 存全行原始 JSON（详情按需读）。

## API（Base `/api`）

| 接口 | 说明 |
|---|---|
| `POST /scan?mode=incremental\|full` | 触发扫描（异步） |
| `GET /scan/latest` | 最近扫描状态（前端轮询 3s） |
| `GET /overview` | 总量/今日/本周、cache_read 占比、按模型分布 + 成本占比 |
| `GET /aggregate?dim=skill\|tool\|project\|model&granularity=day\|week&start&end&project&session` | 通用堆叠聚合，dates + series[]（>12 并入 Other） |
| `GET /projects?sort=tokens\|price\|sessions\|messages&order=` | 项目列表 |
| `GET /projects/{id}` / `/projects/{id}/sessions` | 项目详情 / 会话列表 |
| `GET /sessions/{sid}/timeline` | 完整时间轴（含子会话嵌套树） |
| `GET /messages/{row_uuid}` | 单条详情（全文、工具、usage、价格、子会话引用） |
| `GET/PUT/DELETE /prices/{model}` | 价格 CRUD（PUT 为部分更新语义） |
| `POST /prices/default` | 以 `*` 兜底价批量补齐未定价模型 |
| `GET /models` | 去重模型列表 |

所有聚合与详情**同时返回 tokens 与 price**（价格按 `model_prices` 实时计算），前端仅切换显示模式。

## 定价

`model_prices` 单价为 USD / 1M tokens；`*` 为兜底行。成本公式：

```
input × input_price + cache_read × cache_read_price
  + cache_creation × cache_creation_price + output × output_price   （÷ 1M）
```

内置价格均为参考/占位值，请按实际账单在「价格配置」页修改。
