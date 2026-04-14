# Phase 4: Sync、Search、Wiki、Query 链路隔离
## 目标

将当前全局扫描、全局索引、全局回写的后台链路改造为工作区作用域，确保搜索、Wiki、问答和治理链路不会跨工作区污染数据。

## 前置条件

- 请求上下文与接口鉴权已具备。
- `workspace_id` 已进入核心表结构与路径系统。
- 当前工作区目录可被独立解析。

## 任务清单

- 改造 `sync`：
  - 只扫描当前工作区 `reports/`
  - `sync_jobs` 记录当前 `workspace_id`
  - 增量与全量模式都不得影响其他工作区
- 改造 `search_index`：
  - 增加 `workspace_id`
  - 查询默认按工作区过滤
  - 标签、域名、统计结果按工作区计算
- 改造 `wiki`：
  - `knowledge/` 目录改为当前工作区目录
  - `wiki refresh` 只重建当前工作区索引
  - `slug` 唯一性收敛到工作区内
- 改造 `query`：
  - 问答来源只检索当前工作区 `report/wiki`
  - `question_runs` 带 `workspace_id`
  - writeback 只写当前工作区 question page / task
- 改造 `compile / lint / governance`：
  - compile 只消费当前工作区对象
  - lint 只检查当前工作区知识文件
  - `tasks / conflicts` 仅展示当前工作区结果

## 交付物

- 后台任务隔离规则文档。
- FTS 与 Wiki 索引改造方案。
- Query / Writeback / Compile / Lint 的工作区边界说明。

## 验收标准

- A 工作区执行 sync 不会扫到 B 工作区报告。
- 搜索结果、标签统计、域名统计均只来自当前工作区。
- Wiki 页面、相关报告、问答来源不会跨工作区串联。
- writeback、compile、lint、task、conflict 只落在当前工作区。

## 风险与注意事项

- 这是最容易遗漏的阶段，若改造不完整，会出现“接口已鉴权但后台链路仍串数据”的严重问题。
- FTS 表和 Wiki 索引若不带 `workspace_id`，后续问题很难排查。
