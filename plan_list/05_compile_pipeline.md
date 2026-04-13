# Phase 5: Knowledge Compile 编译链路

## 目标

将新报告编译为知识提案或安全更新，建立 `report -> wiki` 的最小闭环。

## 前置条件

- Wiki 存储与索引已可用。
- 已定义 `knowledge_tasks` 与 `knowledge_conflicts` 数据结构。

## 任务清单

- 扩展数据库，增加：
  - `knowledge_tasks`
  - `knowledge_conflicts`
- 实现 `LLMService` 抽象层。
- 增加 `prompts/compile/` 模板。
- 实现 `compile_service.py`：
  - 抽取实体
  - 抽取概念
  - 生成知识提案
  - 判断是否属于安全更新
- 实现 `POST /api/wiki/compile`
- 支持两种模式：
  - `propose`
  - `apply_safe`
- 让编译结果写入：
  - 新 Wiki 页面
  - Wiki 页面更新
  - `knowledge_tasks`
  - `knowledge_conflicts`

## 交付物

- `llm_service.py`
- `compile_service.py`
- `POST /api/wiki/compile`
- 编译 prompt 模板

## 验收标准

- 指定 `report_id` 可触发单篇报告编译。
- `propose` 模式不会直接覆盖高风险知识页。
- `apply_safe` 只会应用文档定义的低风险更新。
- 新实体或新概念可生成可读的知识页提案。
- 存在明显冲突时会写入 `knowledge_conflicts`，而不是静默覆盖。
- LLM 调用失败时主流程不崩溃，会写入待处理任务或错误记录。

## 风险与注意

- 默认不要自动改写页面摘要和关键结论。
- 编译结果必须保留证据链，不允许无来源写入知识页。
