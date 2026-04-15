# Report 删除改造计划

## 目标

补齐当前系统缺失的 `report` 业务删除能力，使删除不再依赖“手动删文件 + `/api/sync` 被动清理”，而是提供正式的产品级删除链路。

本次改造目标包括：

- 提供 `report` 删除 API
- 提供前端删除入口
- 支持软删除
- 支持延迟物理清理
- 联动搜索索引、对象存储、本地文件、Wiki 关系和审计日志

## 当前缺口

当前系统存在以下问题：

1. 用户侧没有正式删除 `report` 的 API
2. 前端没有删除入口
3. 只有同步扫描在发现文件消失时才会被动删除报告记录
4. 没有“软删除 -> 延迟清理 -> 物理删除”的生命周期
5. 没有删除审计

## 设计原则

1. 先软删除，再延迟物理清理
2. 用户删除动作必须走业务 API，不依赖手工删文件
3. 删除必须以当前工作区 / 当前用户为边界
4. 搜索、列表、详情默认屏蔽已删除报告
5. 对象存储和本地副本清理由后台任务统一执行

## 实现顺序

1. `01_delete_scope_and_lifecycle.md`
2. `02_api_and_schema_upgrade.md`
3. `03_backend_delete_flow_and_cleanup.md`
4. `04_frontend_delete_entry_and_behavior.md`
5. `05_job_runner_audit_and_acceptance.md`
