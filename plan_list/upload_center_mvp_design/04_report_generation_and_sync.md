# Phase 4: AI 报告生成与入库同步

## 目标

把抽取文本转成标准报告 Markdown，并复用现有 `/api/sync` 与可选 `/api/wiki/compile`，完成上传入口到报告中心主链路的闭环。

## 前置条件

- 文件抽取和中间产物落地已完成。
- 现有报告同步与编译 API 已可用。

## 任务清单

- 实现上传任务的报告生成服务。
- 复用现有报告元数据契约生成标准 Markdown：
  - `report_id`
  - `title`
  - `source_ref`
  - `source_type = upload_file`
  - `generated_at`
  - `tags`
- 约定上传报告默认字段：
  - `skill_name = upload_center`
  - `source_domain = upload`
- 实现 `GET /api/uploads/{upload_id}/report-preview`。
- 处理成功后调用 `/api/sync` 入库。
- 如 `auto_compile = true`，调用 `/api/wiki/compile`：
  - `propose`
  - `apply_safe`
- 回填 `report_id_ref`、完成时间和最终状态。

## 交付物

- 上传报告生成模块
- 报告预览接口
- 与 `sync` / `compile` 的对接逻辑
- 上传任务与报告的关联回填逻辑

## 验收标准

- 成功上传并处理的任务会生成标准报告文件到 `reports/`。
- 生成的报告能被现有 `/api/reports` 正常读取。
- `report_id_ref` 会回填到 `upload_jobs`。
- `GET /api/uploads/{upload_id}/report-preview` 可查看生成内容。
- 启用 `auto_compile` 后，上传报告可进入现有编译链路。
- AI 输出缺失必要元数据或正文为空时，不允许静默 sync 成功。

## 风险与注意事项

- 不要让上传链路绕过现有 `sync`，否则会导致索引和报告元数据不一致。
- 首版优先保证“生成标准报告”，不要在上传阶段直接写 Wiki 页面。

