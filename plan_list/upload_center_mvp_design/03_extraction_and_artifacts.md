# Phase 3: 文本抽取与中间产物管理

## 目标

把上传文件稳定转成可处理文本，并把关键中间产物落盘与入库，保证失败可诊断、流程可追踪。

## 前置条件

- 上传任务创建、查询、文件落盘已可用。
- 已明确支持文件类型范围和状态字段契约。

## 任务清单

- 实现 `POST /api/uploads/{upload_id}/process`。
- 为不同文件类型接入抽取逻辑：
  - `txt`
  - `md`
  - `html`
  - `pdf`
  - `docx`
- 将抽取结果标准化为纯文本或 Markdown。
- 将中间产物写入：
  - `uploads/working/{upload_id}/`
  - `raw/uploads/`
  - `upload_artifacts`
- 实现 `GET /api/uploads/{upload_id}/raw`。
- 细化状态推进：
  - `stored`
  - `extracting`
  - `normalizing`
  - `error`
- 对抽取失败、空文本、异常内容写入错误信息。

## 交付物

- 上传处理入口 API
- 文件抽取模块
- 中间产物记录机制
- 原始抽取内容查看接口

## 验收标准

- 已上传任务可被手动触发处理。
- 成功处理的任务能产出至少一个 `extracted_text` 类产物。
- `GET /api/uploads/{upload_id}/raw` 可返回抽取后的文本内容。
- 抽取失败时任务状态更新为 `failed/error` 或 `needs_review/error`。
- 失败任务可看到明确 `error_code` 和 `error_message`。
- 中间产物路径都在允许目录内，不会越权写文件。

## 风险与注意事项

- PDF、DOCX 抽取质量可能不稳定，首版要接受 `needs_review` 分支。
- 不要在本阶段引入复杂 LLM 编排，先把抽取链路做扎实。

