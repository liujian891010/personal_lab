# Report Center + LLM Wiki 计划索引

本目录基于以下两份设计文档拆分为可执行阶段，供逐步实施与验收：

- `docs/REPORT_CENTER_MVP_DESIGN.md`
- `docs/REPORT_CENTER_LLM_WIKI_V2_DESIGN.md`

## 执行顺序

1. `01_project_bootstrap_and_contracts.md`
2. `02_report_storage_and_sync.md`
3. `03_report_read_and_search_api.md`
4. `04_wiki_storage_and_indexing.md`
5. `05_compile_pipeline.md`
6. `06_query_and_writeback.md`
7. `07_governance_and_lint.md`
8. `08_frontend_and_delivery.md`

## 分阶段原则

- 先稳定底座：配置、目录、数据库、路径约束、同步机制。
- 先做 Report，再做 Wiki；先做结构化存取，再做智能编译。
- 先做可验证的 API，再做 LLM 相关能力。
- 先做人工可审核流程，再逐步提高自动化等级。

## 总体验收标准

- 本地 `raw/`、`reports/`、`knowledge/` 目录可作为唯一数据源稳定读取。
- SQLite schema 可初始化且支持 Report 与 Wiki 双层索引。
- Report 列表、详情、全文搜索可正常工作。
- Wiki 页面可读、可索引、可按 `slug` 稳定访问。
- 编译、问答、回写、治理任务具备最小可运行闭环。
- 自动化流程默认安全，不会在无审核情况下覆盖高风险知识页。
