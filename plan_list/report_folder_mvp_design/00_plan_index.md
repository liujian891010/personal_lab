# Report Folder MVP 排期索引

本目录用于承接 `reports` 的文件夹管理需求，目标是为现有 Report Center 增加一套可执行、可验收的“归档与拖拽管理”能力。

## 本次需求范围

- 在 `reports` 中新增文件夹概念
- 支持用户自定义文件夹名称
- 支持将报告拖动到文件夹中
- 支持上传时直接选择目标文件夹
- 支持按文件夹查看和管理报告

## MVP 范围收敛

- MVP 只做单层文件夹，不做多级树形目录
- 一个报告在 MVP 中只归属一个文件夹
- 一个上传任务在创建时最多绑定一个目标文件夹
- 删除文件夹时，默认要求先清空，或显式迁移到 `Unfiled`
- 拖拽仅覆盖 `reports` 列表页，不扩展到 `wiki` 或其他模块

## 执行顺序

1. `01_domain_and_schema.md`
2. `02_folder_api_and_backend_rules.md`
3. `03_report_and_upload_integration.md`
4. `04_frontend_folder_workspace.md`
5. `05_drag_drop_and_move_flow.md`
6. `06_delivery_and_acceptance.md`

## 分阶段原则

- 先收口数据模型和约束，再开放 API
- 先保证“上传可选文件夹 + 报告可归档”主链路可用，再补拖拽体验
- 先实现单项移动与基础管理，再考虑批量操作和树形结构
- 不破坏现有 `reports / uploads / search / wiki` 主流程

## 总体验收标准

- 用户可以创建、重命名、删除文件夹
- `reports` 页面可以按文件夹查看报告
- 报告可以通过操作按钮或拖拽移动到指定文件夹
- 上传文件时可以指定目标文件夹，上传生成的报告自动归档到该文件夹
- 现有未归档报告保持可访问，并能归入 `Unfiled`
- 文件夹变更不会破坏现有报告详情、搜索、上传、同步和 wiki 编译链路
