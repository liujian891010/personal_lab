# Phase 7: Governance 治理与 Lint

## 目标

让知识库具备持续整理能力，能发现冲突、孤儿页、重复页和待补全主题，而不是越积越乱。

## 前置条件

- 编译和问答链路已可用。
- `knowledge_tasks` 和 `knowledge_conflicts` 已落地。

## 任务清单

- 实现 `lint_service.py`
- 增加 `prompts/lint/` 模板。
- 实现 `POST /api/wiki/lint`
- 实现 Lint 规则：
  - 高频命中但缺少页面
  - 重复页面
  - 孤儿页
  - 失效引用
  - 引用已删除报告
  - 长期未更新但高频命中
  - 开放状态冲突
- 实现治理接口：
  - `GET /api/wiki/tasks`
  - `GET /api/wiki/conflicts`
- 生成治理输出：
  - `knowledge_tasks`
  - `knowledge_conflicts`
  - `digests/` 汇总文档

## 交付物

- `lint_service.py`
- `task_service.py`
- `conflict_service.py`
- Lint 与治理接口

## 验收标准

- `POST /api/wiki/lint` 能跑通并产生结构化结果。
- 发现冲突时可生成冲突记录。
- 发现缺页主题时可生成 `fill_gap` 任务。
- 发现可回写但未沉淀的问题时可生成 `review_answer_writeback` 任务。
- `GET /api/wiki/tasks` 和 `GET /api/wiki/conflicts` 可分页返回数据。
- 治理结果不会直接修改知识页正文，除非经过明确审核流程。

## 风险与注意

- Lint 应优先做规则型检查，避免首版全靠 LLM 判断。
- 冲突管理必须显式可见，不能只体现在日志中。
