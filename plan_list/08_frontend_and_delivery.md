# Phase 8: 前端工作台、Skill 对接与交付

## 目标

完成可用的前端工作台，并打通 openclaw Skill 对接，形成从来源输入到报告、Wiki、问答、治理的完整使用路径。

## 前置条件

- 后端 API 已覆盖 Report、Wiki、Compile、Query、Lint、Task、Conflict。
- 目录结构和数据库 schema 已稳定。

## 任务清单

- 初始化 `frontend/` 工程。
- 实现页面：
  - `/reports`
  - `/reports/:reportId`
  - `/wiki`
  - `/wiki/:slug`
  - `/ask`
  - `/tasks`
  - `/conflicts`
  - `/admin`
- 实现核心组件：
  - Report 列表与详情
  - Wiki 页面阅读器
  - 搜索框与筛选器
  - 问答面板
  - 任务列表
  - 冲突列表
  - 同步/编译/Lint 操作面板
- 完成 openclaw Skill 对接：
  - 抓取原始内容到 `raw/`
  - 生成报告到 `reports/`
  - 触发 `/api/sync`
  - 可选触发 `/api/wiki/compile`
- 输出运行说明和最小部署文档。

## 交付物

- 前端可运行工程。
- 与后端联调完成的工作台。
- Skill 对接说明与运行说明。

## 验收标准

- 用户可以从前端看到报告列表、知识页、问答结果、治理任务和冲突项。
- 新报告生成后，能通过同步出现在前端。
- 触发编译后，知识页或编译提案可在前端查看。
- 问答结果可以展示证据页和支撑报告。
- 管理台可以手动触发：
  - 同步
  - 编译
  - Lint
- 提供一套明确的本地启动方式，能让开发者从零启动系统。

## 风险与注意

- 前端首版以可用为目标，不急于做复杂图谱。
- Skill 对接优先走 `Level 2`：自动生成提案，人工审核落地。
