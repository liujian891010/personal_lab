# Phase 1: 项目骨架与契约收口

## 目标

建立可启动的后端项目骨架，固定配置项、目录结构和核心契约，确保后续开发都基于同一套字段与路径规范。

## 前置条件

- 已确认设计文档为当前实施依据。
- 工作区允许创建 `backend/`、`data/`、`raw/`、`reports/`、`knowledge/` 等目录。

## 任务清单

- 初始化 `backend/app` 项目结构。
- 增加 `main.py`、`config.py`、`db.py`、基础 `routers/` 和 `schemas/` 目录。
- 固化配置项：
  - `RAW_ROOT`
  - `REPORTS_ROOT`
  - `KNOWLEDGE_ROOT`
  - `SQLITE_PATH`
  - `LLM_MODEL`
- 初始化 `raw/`、`reports/`、`knowledge/`、`data/`、`logs/` 目录。
- 明确并落地字段契约：
  - Report 主来源字段为 `source_ref`
  - `source_url` 为兼容字段
  - Wiki 页面 `slug` 全局唯一
- 落地统一路径安全函数，阻止目录穿越和根目录逃逸。
- 实现 `GET /api/health`。

## 交付物

- 可启动的 FastAPI 项目骨架。
- 基础配置与目录初始化逻辑。
- 路径校验与文件根目录解析工具。
- 健康检查接口。

## 验收标准

- 服务可通过 `uvicorn app.main:app --reload --port 8000` 启动。
- 首次启动后，缺失的基础目录能被自动创建或给出明确错误提示。
- `GET /api/health` 能返回：
  - 服务状态
  - 各根目录是否存在
  - SQLite 是否可连接
- 非法路径如 `../x.md`、绝对路径、跨根目录路径会被拒绝。
- 代码中不存在 `source_ref` / `source_url` 契约冲突。

## 风险与注意

- 不要在这一阶段引入 LLM SDK。
- 不要把业务逻辑写进路由层。
