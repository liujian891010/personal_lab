# 02 API 与 Schema 升级

## 目标

增加删除 API，并补齐支撑删除生命周期的数据库字段。

## API 设计

新增接口：

```http
DELETE /api/reports/{report_id}
```

行为：

- 校验当前用户工作区内是否存在该报告
- 执行软删除
- 返回 `204 No Content`

可选扩展接口：

```http
POST /api/reports/{report_id}/restore
```

当前阶段可先不做恢复，只设计删除。

## Schema 建议

在 `reports` 表增加：

- `deleted_at TEXT`
- `deleted_by TEXT`
- `purge_after TEXT`
- `storage_cleanup_status TEXT NOT NULL DEFAULT 'pending'`

在 `sync_jobs` 之外新增专门清理任务表，建议：

```text
report_cleanup_jobs
```

字段建议：

- `id`
- `report_id_ref`
- `job_type`
- `status`
- `scheduled_at`
- `started_at`
- `finished_at`
- `message`

## 查询规则调整

以下查询默认增加过滤：

- `reports` 列表
- `reports` 详情
- `search_index` 相关检索
- `query_service` 的报告召回
- `wiki compile` 候选报告选择

默认条件：

```sql
deleted_at IS NULL
```

## 索引建议

增加索引：

- `idx_reports_deleted_at`
- `idx_reports_purge_after`
- `idx_reports_storage_cleanup_status`
