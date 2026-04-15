# 03 后端删除流程与清理联动

## 目标

定义后端删除动作如何联动 DB、搜索索引、对象存储和本地文件副本。

## 软删除流程

删除 API 命中后执行：

1. 校验报告存在且归属当前用户
2. 更新 `reports.deleted_at`
3. 更新 `reports.deleted_by`
4. 更新 `reports.purge_after = now + 7 days`
5. 更新 `reports.storage_cleanup_status = 'pending'`
6. 从 `search_index` 删除该报告索引
7. 保留 `report_tags` / `report_links` / `page_sources` 关系记录，等待最终清理
8. 写入审计日志

## 物理清理流程

后台清理任务周期扫描：

```text
deleted_at IS NOT NULL
AND purge_after <= now
AND storage_cleanup_status IN ('pending', 'failed')
```

然后执行：

1. 删除对象存储正文对象
2. 删除本地兼容文件副本
3. 删除 `report_links`
4. 删除 `report_tags`
5. 删除 `page_sources`
6. 删除 `reports`
7. 更新清理任务状态

## 与 Wiki 的关系

已删除 `report` 若仍被 wiki 页面引用，建议：

1. 第一阶段先允许删除
2. 删除后 `page_sources` 在最终清理时移除
3. wiki 页面在后续 `refresh_index` / lint / compile 中暴露“证据已失效”

不要在第一阶段把删除操作阻塞在“必须先清理 wiki 引用”上，否则操作成本过高。

## 与对象存储的关系

当前系统已存储：

- `storage_provider`
- `storage_bucket`
- `object_key`

清理逻辑应优先按对象指针删除对象；若无对象指针，再回退删本地路径。

## 与同步流程的关系

`sync_service` 需要避免把“已软删除但文件仍在本地”的报告重新同步回来。

建议规则：

- 若 `report_id` 已存在且 `deleted_at IS NOT NULL`，默认跳过，不自动恢复
- 恢复必须走单独恢复接口
