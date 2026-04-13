# Phase 3: Report 阅读与搜索 API

## 目标

让 Report 层具备稳定可调用的列表、详情、原文和搜索接口，形成第一层可用产品能力。

## 前置条件

- Report 同步链路已完成。
- SQLite 和 FTS 可正常写入。

## 任务清单

- 实现 `GET /api/reports`
- 实现 `GET /api/reports/{report_id}`
- 实现 `GET /api/reports/{report_id}/raw`
- 实现 `GET /api/search`
- 实现 `GET /api/tags`
- 实现 `GET /api/domains`
- 完成分页、排序、筛选逻辑：
  - `tag`
  - `source_domain`
  - `skill_name`
  - `status`
  - `date_from`
  - `date_to`
- 实现 FTS5 搜索结果摘要和高亮片段。
- 统一 API 返回字段，确保包含：
  - `source_ref`
  - `source_url`
  - `source_domain`
  - `source_type`

## 交付物

- `reports.py`
- `search.py`
- `taxonomy.py`
- `report_service.py`
- `search_service.py`

## 验收标准

- 列表接口可按时间倒序返回报告。
- 详情接口可返回正文、元数据、标签和外链。
- 原始接口能返回完整 Markdown 原文。
- 搜索接口可在标题、摘要、正文中命中关键词。
- 标签和域名聚合接口返回统计结果。
- 所有接口对不存在的 `report_id` 返回明确 404。
- API 返回字段与设计文档一致，不出现同一语义多套命名。

## 风险与注意

- 中文搜索首版接受 FTS5 限制，不提前引入复杂分词方案。
- 搜索接口先求稳定和可解释，不急于做相关性学习。
