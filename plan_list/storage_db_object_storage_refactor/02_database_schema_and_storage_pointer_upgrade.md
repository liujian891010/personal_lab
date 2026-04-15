# Phase 2: 数据库 Schema 与存储指针升级

## 目标

把当前依赖本地文件路径的表结构，升级成可以稳定指向对象存储对象的结构，同时兼容迁移期双读。

## 改造步骤

- 梳理受影响表
  - `upload_jobs`
  - `upload_artifacts`
  - `reports`
  - `wiki` 相关表
  - 任何保存 `file_path/storage_path/source_ref` 的表
- 为表增加对象存储字段
  - `storage_provider`
  - `storage_bucket`
  - `object_key`
  - `object_version`
  - `content_hash`
  - `byte_size`
  - `storage_status`
- 保留旧字段作为迁移期兼容字段
  - 例如 `legacy_file_path`
  - 迁移完成后再评估是否移除
- 为常用读取路径建索引
  - `workspace_id + object_key`
  - `upload_id_ref + artifact_kind`
  - `report_id + workspace_id`
- 设计双读策略
  - 优先读对象存储字段
  - 缺失时回退读旧本地路径字段
- 设计回填校验字段
  - `migrated_at`
  - `migration_batch_id`
  - `migration_verified`

## 风险点

- 旧代码仍直接拼接本地路径
- 迁移期间出现元数据存在但对象缺失
- 多模块对 `file_path` 字段语义不一致
