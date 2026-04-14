# Phase 1: 文件夹领域模型与存储结构

## 目标

明确 Report Folder 的数据模型、字段命名、唯一约束和与现有 `reports / uploads` 的关系，为后续 API 和前端交互提供稳定基础。

## 前置条件

- 现有 `reports`、`uploads`、`search_index` 数据结构已稳定运行
- SQLite 迁移方式和初始化脚本已可维护

## 任务清单

- 新增 `report_folders` 表
- 字段建议统一为：
  - `folder_id`
  - `folder_name`
  - `folder_slug`
  - `description`
  - `sort_order`
  - `report_count`
  - `created_at`
  - `updated_at`
- 约束建议：
  - `folder_id` 全局唯一
  - `folder_name` 全局唯一，大小写不敏感
  - `folder_slug` 全局唯一
- 为 `reports` 增加：
  - `folder_id_ref`
- 为 `uploads` 增加：
  - `folder_id_ref`
- 为 `reports.folder_id_ref`、`uploads.folder_id_ref` 建索引
- 定义系统保留逻辑：
  - 默认未归档视图标识为 `Unfiled`
  - `Unfiled` 作为逻辑视图，不强制落库存成真实 folder 记录

## 交付物

- SQLite schema 变更文档
- 表结构与字段命名约定
- 索引与唯一约束说明
- 迁移策略说明

## 验收标准

- 数据库可创建 `report_folders` 表
- 已有 `reports / uploads` 数据可平滑增加 `folder_id_ref`
- 数据层能明确区分“已归档”和“未归档”
- 字段命名、唯一约束和外键引用在文档中无歧义

## 风险与注意事项

- 若后续要支持“一个报告多个文件夹”，当前模型需要重构为关系表
- 若未来要支持多级目录，需要补 `parent_folder_id`
- `folder_name` 和 `folder_slug` 的归一化规则必须先统一，否则后续前后端会分叉
