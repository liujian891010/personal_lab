# Phase 6: Query 问答与回写

## 目标

实现基于 `Wiki + Reports` 的问答能力，并将高价值问答回写为长期知识。

## 前置条件

- Wiki 页面已可编译和读取。
- Report 与 Wiki 双层索引均可用。

## 任务清单

- 扩展数据库，增加：
  - `question_runs`
  - `question_run_sources`
- 实现 `query_service.py`
- 增加 `prompts/query/` 模板。
- 实现 `POST /api/query/ask`
- 实现 Query 召回顺序：
  - 先查 `wiki_pages`
  - 对 `page_type = question` 提权
  - 不足时回退 `reports`
- 实现回答结果返回：
  - 结论
  - 依据
  - 不确定点
  - 下一步建议
- 实现 `POST /api/query/writeback`
- 支持将问答沉淀为：
  - `question` 页面
  - `topic` / `entity` 页面更新
  - `review_answer_writeback` 任务

## 交付物

- `query_service.py`
- `POST /api/query/ask`
- `POST /api/query/writeback`
- 问答运行记录表

## 验收标准

- 一个明确问题可返回可解释答案和证据来源。
- 回答结果可区分 Wiki 证据与 Report 证据。
- 问答历史可被记录到 `question_runs`。
- 高价值问答可回写为 `question` 页面或待审核任务。
- 回写不会破坏已有 Wiki 页面结构。
- 找不到足够证据时系统会明确说明，而不是伪造确定性答案。

## 风险与注意

- 问答层必须优先消费已有知识页，避免重复“现读现答”。
- 回写默认走建议模式，避免一问一写造成知识污染。
