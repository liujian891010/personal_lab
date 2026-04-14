# Phase 2: 工作区存储与 Schema 隔离
## 目标

建立以 `workspace_id` 为核心的存储与数据模型，让数据库记录、本地文件和索引元数据都具备明确归属，为后续访问控制与后台任务隔离打基础。

## 前置条件

- 已确认 `UserContext` 字段契约。
- 已明确隔离主维度采用 `workspace_id`。
- 已确定首版工作区映射策略。

## 任务清单

- 设计工作区目录结构：
  - `storage/workspaces/{workspace_id}/reports/`
  - `storage/workspaces/{workspace_id}/knowledge/`
  - `storage/workspaces/{workspace_id}/uploads/`
  - `storage/workspaces/{workspace_id}/raw/`
  - `storage/workspaces/{workspace_id}/logs/`
- 扩展配置项与路径解析策略，支持按工作区解析根目录。
- 为以下表增加 `workspace_id`：
  - `reports`
  - `report_tags`
  - `report_links`
  - `search_index`
  - `report_folders`
  - `upload_jobs`
  - `upload_artifacts`
  - `sync_jobs`
  - `wiki_pages`
  - `wiki_page_tags`
  - `wiki_links`
  - `page_sources`
  - `knowledge_tasks`
  - `knowledge_conflicts`
  - `question_runs`
  - `question_run_sources`
- 重新审视唯一键与索引：
  - 将全局唯一改为工作区内唯一
  - 关键查询字段增加 `workspace_id` 复合索引
- 设计审计字段补齐策略：
  - `created_by`
  - `updated_by`
  - `triggered_by_user_id`
- 明确路径安全约束：
  - 禁止跨工作区路径穿越
  - 禁止跨工作区文件读取

## 交付物

- 工作区目录结构定义。
- SQLite schema 变更清单。
- 唯一键与复合索引清单。
- 路径解析与安全约束说明。

## 验收标准

- 任一业务对象都可定位到所属 `workspace_id`。
- 同名资源可在不同工作区内共存，不发生全局冲突。
- 任意文件路径都只能在所属工作区根目录内解析。
- Schema 足以支撑后续接口过滤、索引隔离和后台任务隔离。

## 风险与注意事项

- 现有 `file_path / storage_path / slug / source_ref` 都包含全局语义，迁移前必须统一重新定义。
- 若只给主表加 `workspace_id`，而不补从表和索引表，会留下隐形串数问题。
