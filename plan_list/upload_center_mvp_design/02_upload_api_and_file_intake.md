# Phase 2: Upload API 与文件接收

## 目标

实现最小上传 API，完成文件接收、落盘、任务入库和状态初始化，形成可观测的上传入口。

## 前置条件

- Upload 目录与表结构已完成。
- 后端已有基础 FastAPI 路由和统一响应风格。

## 任务清单

- 新增 `uploads` 路由模块。
- 实现 `POST /api/uploads`：
  - 接收 multipart 文件
  - 校验扩展名与 MIME
  - 写入 `uploads/inbox/`
  - 创建 `upload_jobs` 记录
  - 支持 `auto_process`
  - 支持 `auto_compile`
  - 支持 `compile_mode`
  - 支持可选 `title`
  - 支持可选 `tags`
- 实现 `GET /api/uploads`。
- 实现 `GET /api/uploads/{upload_id}`。
- 统一返回字段：
  - `upload_id`
  - `original_filename`
  - `source_ref`
  - `upload_status`
  - `processing_stage`
  - `report_id_ref`
  - `retry_count`
  - `created_at`
  - `updated_at`
- 增加上传尺寸和类型校验。

## 交付物

- `uploads.py` 路由
- `upload_service.py` 或同级服务模块
- 上传任务列表与详情 API
- 文件接收与初始入库逻辑

## 验收标准

- 可通过 API 成功上传 `txt/md/html/pdf/docx` 文件。
- 上传成功后文件落在 `uploads/inbox/`，数据库存在对应 `upload_jobs` 记录。
- `GET /api/uploads` 可分页返回上传列表。
- `GET /api/uploads/{upload_id}` 可稳定返回详情。
- 不支持的文件类型、空文件、超限文件会返回明确 4xx 错误。
- 不存在的 `upload_id` 会返回明确 404。

## 风险与注意事项

- 首版先做单文件上传，不要同时引入批量压缩包上传。
- 返回字段要从一开始固定，避免后续前端和文档频繁改口径。

