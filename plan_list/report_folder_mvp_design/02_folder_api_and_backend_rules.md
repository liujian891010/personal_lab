# Phase 2: 文件夹 API 与后端规则

## 目标

提供稳定的文件夹管理 API，覆盖创建、查询、重命名、删除、移动报告等基础能力，并定义清晰的业务规则。

## 前置条件

- 文件夹表和 `folder_id_ref` 字段已落地
- 后端已有统一的数据库访问和 schema 模式

## 任务清单

- 新增文件夹 API：
  - `GET /api/report-folders`
  - `POST /api/report-folders`
  - `GET /api/report-folders/{folder_id}`
  - `PATCH /api/report-folders/{folder_id}`
  - `DELETE /api/report-folders/{folder_id}`
- 新增报告移动 API：
  - `POST /api/reports/{report_id}/move-folder`
- 可选补充批量移动 API：
  - `POST /api/reports/move-folder`
- 统一返回字段：
  - `folder_id`
  - `folder_name`
  - `folder_slug`
  - `description`
  - `sort_order`
  - `report_count`
  - `created_at`
  - `updated_at`
- 统一业务规则：
  - 重名文件夹禁止创建
  - 删除非空文件夹默认拒绝
  - 支持移动到具体文件夹或移动回 `Unfiled`
  - `report_count` 需与实际数据一致
- 补充错误码和错误消息约定：
  - 名称冲突
  - 文件夹不存在
  - 报告不存在
  - 删除前必须清空

## 交付物

- 文件夹 CRUD API
- 报告移动 API
- 后端 service / repository 层规则实现
- API 契约说明

## 验收标准

- 可以通过 API 创建、查看、修改、删除文件夹
- 可以通过 API 把报告移动到目标文件夹
- 删除非空文件夹时返回明确错误
- 文件夹统计数在新增、移动、删除后正确更新

## 风险与注意事项

- `report_count` 若采用缓存字段，需要保证事务内更新
- 若拖拽高频触发移动，需要保证接口幂等或最终一致
- 删除文件夹时要避免悬挂的 `folder_id_ref`
