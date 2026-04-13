# Phase 1: Upload 存储与数据契约

## 目标

建立 Upload Center 的目录结构、数据库表和核心字段契约，确保后续处理链路都建立在统一标识和状态模型上。

## 前置条件

- 现有 `backend/`、`data/`、`raw/`、`reports/` 已可正常使用。
- 已确认报告主链路字段仍以 `report_id`、`source_ref`、`source_type` 为准。

## 任务清单

- 初始化目录：
  - `uploads/inbox/`
  - `uploads/working/`
  - `uploads/processed/`
  - `uploads/failed/`
  - `raw/uploads/`
- 扩展配置项：
  - `UPLOADS_ROOT`
  - `UPLOAD_INBOX_ROOT`
  - `UPLOAD_WORKING_ROOT`
  - `UPLOAD_PROCESSED_ROOT`
  - `UPLOAD_FAILED_ROOT`
- 落地 `upload_jobs` 表。
- 落地 `upload_artifacts` 表。
- 固化字段契约：
  - `upload_id` 全局唯一
  - `source_ref` 使用 `upload://{upload_id}/{original_filename}`
  - `source_type` 固定为 `upload_file`
  - `upload_status` 与 `processing_stage` 分离
- 为上传目录读写增加统一路径安全校验。

## 交付物

- Upload Center 目录初始化逻辑
- Upload 相关配置项
- SQLite schema 扩展
- Upload 主字段与状态字段契约说明

## 验收标准

- 服务启动后能自动创建缺失的上传目录，或给出明确报错。
- SQLite 中存在 `upload_jobs` 和 `upload_artifacts` 表及必要索引。
- 同名文件多次上传不会导致 `upload_id`、`source_ref`、`storage_path` 冲突覆盖。
- 任意上传任务都可稳定生成唯一 `upload_id`。
- 非法路径、目录穿越、跨根目录写入会被拒绝。

## 风险与注意事项

- 不要把上传文件直接写入 `reports/`，否则会破坏处理阶段边界。
- `source_ref` 必须延续现有报告主字段语义，不要引入第二套来源主键。

