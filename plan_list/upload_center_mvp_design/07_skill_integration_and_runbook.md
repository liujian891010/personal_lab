# Phase 7: Skill 对接与运行手册

## 目标

把 Upload Center 纳入现有 openclaw / Report Center / LLM Wiki 体系，补齐操作文档、运行说明和后续扩展约束。

## 前置条件

- Upload Center 主链路和前端工作台已可运行。
- 现有系统运行手册和 Skill 接入手册已存在。

## 任务清单

- 明确 Upload Center 与 openclaw Skill 的职责边界：
  - Skill 负责 URL / 网页 / 视频 ingest
  - Upload Center 负责本地文件 ingest
  - 最终都产出标准报告
- 在运行手册中补充：
  - 上传支持格式
  - 上传处理流程
  - 失败重试说明
  - 自动编译说明
- 在 Skill 接入文档中补充：
  - 何时走 `POST /api/uploads`
  - 何时继续直接写 `reports/`
  - `source_ref`、`source_type`、`report_id` 的统一约束
- 评估是否需要在管理台增加上传统计卡片。
- 为后续演进预留接口说明：
  - 批量上传
  - 上传后人工确认再 sync
  - OCR / 多模态抽取

## 交付物

- Upload Center 运行说明
- Upload 与 Skill 协同接入规范
- 补充后的系统操作文档

## 验收标准

- 新成员可仅依据文档完成上传中心的启动、使用和排错。
- Skill 与 Upload Center 的边界清晰，不会出现重复入库或职责冲突。
- 上传文件和 Skill 报告最终都能进入同一 Report Center / Wiki 主链路。
- 后续扩展方向在文档中有明确保留位。

## 风险与注意事项

- 文档必须保持和实际 API、字段命名一致，避免再次出现多套叫法。
- 不要让 Upload Center 演变成与 Skill 并行的一套“第二知识系统”。
