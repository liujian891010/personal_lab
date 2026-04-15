# Phase 1: 目标架构与存储契约

## 目标

明确线上目标形态，先统一“什么进数据库、什么进对象存储、什么只做临时缓存”，避免后续每个模块各自定义一套路径规则。

## 改造步骤

- 明确三层存储边界
  - 数据库存：上传任务、报告元数据、artifact 索引、搜索索引、任务状态、权限、审计记录
  - 对象存储存：原始文档、抽取文本、报告正文、知识库产物
  - 本地磁盘存：处理中间文件、短期缓存、失败重试暂存
- 统一对象 key 规则
  - `workspaces/{workspace_id}/uploads/original/...`
  - `workspaces/{workspace_id}/uploads/extracted/...`
  - `workspaces/{workspace_id}/reports/...`
  - `workspaces/{workspace_id}/knowledge/...`
  - `workspaces/{workspace_id}/logs/...` 视需求决定是否上云
- 统一存储指针格式
  - 数据库中不再默认存本地相对路径
  - 改为存 `storage_provider + bucket + object_key + version_id + content_hash + byte_size`
- 统一读写接口
  - 抽象 `StorageService`
  - 规范 `put/get/head/delete/presign/copy`
- 明确临时目录回收策略
  - `working/tmp` 按任务完成时间清理
  - 失败文件按保留期延迟删除

## 交付物

- 存储架构图
- 对象 key 规范文档
- `StorageService` 接口契约
- 存储字段命名规范
