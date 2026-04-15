# 存储改造计划总览

本次改造目标是把当前“SQLite + 本地磁盘目录”的混合存储，演进为“关系数据库存元数据 + 对象存储存文件正文 + 本地仅保留临时处理缓存”的生产方案，并保持现有 `workspace_id` 级别的数据隔离能力。

## 改造范围

- 上传原文件从本地目录迁移到对象存储
- 抽取文本、报告 Markdown、知识库产物从本地目录迁移到对象存储
- SQLite 中的文件路径字段演进为对象存储 URI / key
- 本地磁盘仅保留 `inbox / working / tmp` 等短期缓存
- 引入配额、生命周期清理、迁移回填、运维回滚方案

## 分步计划

1. `01_target_architecture_and_storage_contract.md`
2. `02_database_schema_and_storage_pointer_upgrade.md`
3. `03_upload_pipeline_to_object_storage.md`
4. `04_report_wiki_query_read_write_refactor.md`
5. `05_migration_backfill_and_dual_read_cutover.md`
6. `06_quota_retention_and_cost_control.md`
7. `07_ops_security_and_delivery_runbook.md`

## 核心原则

- 数据库只存元数据、索引、状态、权限、存储指针
- 文件正文统一存对象存储，不继续长期占用应用机磁盘
- 本地目录只保留临时缓存，处理完成后可回收
- 所有对象存储 key 必须带 `workspace_id`
- 全链路支持灰度、回滚、双读、迁移校验
