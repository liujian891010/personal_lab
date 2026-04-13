# Phase 2: Report 存储、解析与同步

## 目标

打通 `reports/` 目录到 SQLite 的同步链路，让报告文件可被可靠扫描、解析、入库和更新。

## 前置条件

- 已完成项目骨架、配置和路径安全。
- 已确认 Report front matter 格式。

## 任务清单

- 编写 `schema.sql`，实现 MVP Report 相关表：
  - `reports`
  - `report_tags`
  - `report_links`
  - `search_index`
  - `sync_jobs`
- 实现数据库初始化逻辑。
- 实现 front matter 解析器。
- 实现 Markdown 正文提取与 `content_hash` 计算逻辑。
- 实现目录扫描器：
  - 扫描 `reports/**/*.md`
  - 解析 front matter
  - 计算 `file_path`、`mtime`、`size`、`content_hash`
- 实现 `incremental` / `full` 两种同步模式。
- 同步时维护：
  - `reports`
  - `report_tags`
  - `report_links`
  - `search_index`
  - `sync_jobs`

## 交付物

- 可执行的数据库 schema。
- `sync_service.py`
- front matter / Markdown / hash 处理模块。
- `POST /api/sync`

## 验收标准

- 空库首次启动可自动初始化 schema。
- 新增一篇报告后执行 `incremental` 可成功入库。
- 修改报告正文后再次同步能识别为更新。
- 删除报告文件后同步能清理数据库记录和搜索索引。
- `content_hash` 计算范围与设计文档一致，只针对正文部分。
- `POST /api/sync` 返回扫描数、创建数、更新数、删除数、失败数。
- 单篇解析失败不会阻塞其他报告同步。

## 风险与注意

- 不要在同步阶段做问答或知识编译。
- 失败报告需进入错误日志或失败记录，不要混入正常索引结果。
