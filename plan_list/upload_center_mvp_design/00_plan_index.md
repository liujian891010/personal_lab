# Upload Center MVP 排期索引

本目录基于以下设计文档拆分为可执行阶段，供逐步实施与验收：

- `plan_list/09_upload_center_mvp_design.md`
- `docs/REPORT_CENTER_MVP_DESIGN.md`
- `docs/REPORT_CENTER_LLM_WIKI_V2_DESIGN.md`

## 执行顺序

1. `01_storage_and_schema.md`
2. `02_upload_api_and_file_intake.md`
3. `03_extraction_and_artifacts.md`
4. `04_report_generation_and_sync.md`
5. `05_frontend_upload_workspace.md`
6. `06_retry_review_and_governance.md`
7. `07_skill_integration_and_runbook.md`

## 分阶段原则

- 先固化目录、表结构、主字段约束，再接 API。
- 先打通“上传 -> 生成标准报告 -> sync”，再接入 compile。
- 先保证失败可观测、可重试，再做自动化增强。
- 上传中心只新增 ingest 入口，不破坏既有 Report Center / LLM Wiki 主链路。

## 总体验收标准

- 上传文件可形成唯一 `upload_id`，并全程可追踪状态。
- 成功上传任务能生成标准报告，并进入现有 `reports` 与 `search_index`。
- 启用 `auto_compile` 时，上传报告可复用现有 `wiki compile` 流程。
- 前端能查看上传列表、详情、状态、错误、原文和关联报告。
- 失败任务具备明确错误原因、重试能力和人工审核入口。

