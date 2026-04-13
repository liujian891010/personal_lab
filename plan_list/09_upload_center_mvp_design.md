# Upload Center MVP 设计文档

> 本文档是 `Report Center + LLM Wiki` 的增量设计，目标是在现有「报告入库 -> 检索 -> 编译 -> Wiki 治理」链路之上，增加一个标准化上传入口。
>
> 设计原则：上传不是另一套独立系统，而是新的 `ingest` 入口。最终产物仍然是标准 `report`，并继续复用现有 `sync`、`compile`、`query`、`lint`、`writeback` 流程。

## 1. 目标

### 1.1 核心目标

- 支持用户从前端或 API 上传本地文件。
- 上传文件进入标准 AI 处理流水线，生成结构化报告并入库。
- 生成后的报告继续沿用现有 `reports/`、`SQLite`、`FTS`、`Wiki compile` 机制。
- 为上传任务提供明确状态、错误信息、重试能力和人工审核入口。

### 1.2 解决的问题

- 现在系统主要依赖 openclaw Skill 直接产出报告，缺少手动上传入口。
- 用户手上的 `pdf/docx/txt/md/html` 等文件无法直接纳入报告中心。
- 上传处理过程不可见，缺少任务状态、失败原因和重试管理。

### 1.3 非目标

- 首版不做多租户隔离。
- 首版不做复杂工作流编排平台。
- 首版不直接把上传文件写成 Wiki 页面。
- 首版不支持任意超大附件的分布式异步处理。

---

## 2. 设计定位

Upload Center 在整体架构中的位置如下：

```text
Upload File
  -> Upload Job
  -> Raw Extraction
  -> AI Summarization
  -> Standard Report Markdown
  -> /api/sync
  -> optional /api/wiki/compile
  -> Reports / Wiki / Ask / Governance
```

关键原则：

- 上传文件先成为 `upload job`，再生成标准 `report`。
- `report_id`、`source_ref`、`file_path` 仍是主链路契约，不新造第二套报告标识。
- Upload Center 只负责「接入、处理、观测、重试」，不替代现有 Report Center。

---

## 3. 目录结构

建议在现有项目目录上新增：

```text
uploads/
├── inbox/
│   └── 2026/04/
├── working/
│   └── {upload_id}/
├── processed/
│   └── 2026/04/
└── failed/
    └── 2026/04/

raw/
└── uploads/
    └── 2026/04/

reports/
└── 2026/04/
```

目录职责：

- `uploads/inbox/`：保存原始上传文件，作为最初接收区。
- `uploads/working/{upload_id}/`：处理中的中间产物，例如文本抽取结果、切片结果、模型响应快照。
- `uploads/processed/`：处理完成后的归档文件。
- `uploads/failed/`：失败任务对应的原始文件归档区。
- `raw/uploads/`：标准化后的原始内容快照，供后续审计、复盘、重处理使用。

约束：

- 原始上传文件一旦入库，不允许静默覆盖。
- `working` 目录可清理，但必须保证失败时保留必要诊断信息。
- 最终报告仍落到现有 `reports/` 目录，不另建 `upload_reports/`。

---

## 4. 数据模型

### 4.1 `upload_jobs`

```sql
CREATE TABLE upload_jobs (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id             TEXT NOT NULL UNIQUE,
    original_filename     TEXT NOT NULL,
    stored_filename       TEXT NOT NULL,
    storage_path          TEXT NOT NULL UNIQUE,
    mime_type             TEXT,
    file_ext              TEXT NOT NULL,
    file_size_bytes       INTEGER NOT NULL,
    source_ref            TEXT NOT NULL UNIQUE,
    source_type           TEXT NOT NULL DEFAULT 'upload_file',
    title                 TEXT,
    upload_status         TEXT NOT NULL,
    processing_stage      TEXT NOT NULL,
    report_id_ref         TEXT UNIQUE,
    compile_mode          TEXT,
    auto_compile          INTEGER NOT NULL DEFAULT 0,
    triggered_by          TEXT NOT NULL DEFAULT 'user_upload',
    error_code            TEXT,
    error_message         TEXT,
    retry_count           INTEGER NOT NULL DEFAULT 0,
    content_hash          TEXT,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    completed_at          TEXT,
    FOREIGN KEY (report_id_ref) REFERENCES reports(report_id) ON DELETE SET NULL
);

CREATE INDEX idx_upload_jobs_status ON upload_jobs(upload_status, updated_at DESC);
CREATE INDEX idx_upload_jobs_stage ON upload_jobs(processing_stage, updated_at DESC);
CREATE INDEX idx_upload_jobs_created_at ON upload_jobs(created_at DESC);
CREATE INDEX idx_upload_jobs_report_id_ref ON upload_jobs(report_id_ref);
```

字段约束说明：

- `upload_id`：上传任务稳定标识，建议 `upl_YYYYMMDD_HHMMSS_xxxxxxxx`。
- `source_ref`：主来源字段，上传场景建议使用 `upload://{upload_id}/{original_filename}`。
- `source_type`：固定为 `upload_file`，与现有 `reports.source_type` 契约兼容。
- `report_id_ref`：上传生成报告后的回填字段，一篇上传任务最多对应一个主报告。
- `compile_mode`：仅允许 `propose`、`apply_safe` 或空值。
- `upload_status` 与 `processing_stage` 分开保存，避免状态语义混杂。

### 4.2 `upload_artifacts`

```sql
CREATE TABLE upload_artifacts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id_ref         TEXT NOT NULL,
    artifact_kind         TEXT NOT NULL,
    file_path             TEXT NOT NULL,
    content_hash          TEXT,
    byte_size             INTEGER,
    created_at            TEXT NOT NULL,
    UNIQUE (upload_id_ref, artifact_kind, file_path),
    FOREIGN KEY (upload_id_ref) REFERENCES upload_jobs(upload_id) ON DELETE CASCADE
);

CREATE INDEX idx_upload_artifacts_upload_id_ref ON upload_artifacts(upload_id_ref, artifact_kind);
```

`artifact_kind` 建议值：

- `original_file`
- `extracted_text`
- `normalized_markdown`
- `model_input`
- `model_output`
- `report_preview`
- `error_log`

### 4.3 与现有表的关系

- `upload_jobs.report_id_ref -> reports.report_id`
- 上传生成报告后，标准报告仍进入：
  - `reports`
  - `report_tags`
  - `report_links`
  - `search_index`
- 若开启自动编译，后续继续进入：
  - `wiki_pages`
  - `page_sources`
  - `knowledge_tasks`
  - `knowledge_conflicts`

---

## 5. 状态机

### 5.1 `upload_status`

建议值：

- `uploaded`
- `queued`
- `processing`
- `completed`
- `failed`
- `needs_review`

说明：

- `upload_status` 用于前端列表态和运维态。
- `needs_review` 表示技术上已完成，但需要人工确认后才能继续自动流转。

### 5.2 `processing_stage`

建议值：

- `received`
- `stored`
- `extracting`
- `normalizing`
- `summarizing`
- `report_generating`
- `syncing`
- `compiling`
- `done`
- `error`

### 5.3 流转规则

```text
uploaded/received
  -> queued/stored
  -> processing/extracting
  -> processing/normalizing
  -> processing/summarizing
  -> processing/report_generating
  -> processing/syncing
  -> processing/compiling    (optional)
  -> completed/done
```

失败分支：

```text
任一阶段失败
  -> failed/error
  -> retry
  -> queued/stored
```

人工审核分支：

```text
摘要质量低 / 抽取内容为空 / 格式异常
  -> needs_review/error
```

---

## 6. 处理流水线

### 6.1 标准流水线

1. 接收上传文件并写入 `uploads/inbox/`。
2. 创建 `upload_jobs` 记录，生成 `upload_id` 与 `source_ref`。
3. 根据文件类型执行文本抽取。
4. 将抽取结果写入 `raw/uploads/` 与 `upload_artifacts`。
5. 调用 AI 摘要流程生成标准报告草稿。
6. 按现有报告元数据规范生成 Markdown 报告文件。
7. 调用 `/api/sync` 将报告入库并建立索引。
8. 如启用自动编译，则调用 `/api/wiki/compile`。
9. 回填 `report_id_ref`、完成状态和产物索引。

### 6.2 文件类型处理建议

MVP 首批支持：

- `txt`
- `md`
- `html`
- `pdf`
- `docx`

处理建议：

- `txt`/`md`：直接读取文本并规范化。
- `html`：提取正文后转 Markdown。
- `pdf`：优先文本抽取，失败时进入 `needs_review`。
- `docx`：抽取段落文本和标题结构。

### 6.3 报告生成规则

上传生成的标准报告必须遵守现有 `Report Center MVP` 契约：

- 必须有 `report_id`
- 必须有 `title`
- 必须有 `source_ref`
- `source_type = upload_file`
- `source_url` 默认留空
- 必须写入 `generated_at`
- 必须写入 `tags`
- `summary`、`content_hash`、`skill_name` 应尽量补齐

建议：

- `skill_name` 使用 `upload_center`
- `source_domain` 使用 `upload`

---

## 7. API 设计

### 7.1 上传文件

```http
POST /api/uploads
Content-Type: multipart/form-data
```

表单字段：

- `file`
- `auto_process`：`true | false`
- `auto_compile`：`true | false`
- `compile_mode`：`propose | apply_safe`
- `title`：可选
- `tags`：可选，逗号分隔或多值字段

返回：

```json
{
  "upload_id": "upl_20260413_201530_a1b2c3d4",
  "original_filename": "karpathy_notes.pdf",
  "source_ref": "upload://upl_20260413_201530_a1b2c3d4/karpathy_notes.pdf",
  "upload_status": "uploaded",
  "processing_stage": "received",
  "auto_process": true,
  "auto_compile": false,
  "compile_mode": "propose",
  "created_at": "2026-04-13T20:15:30+08:00"
}
```

### 7.2 上传列表

```http
GET /api/uploads
```

查询参数：

- `status`
- `stage`
- `q`
- `page`
- `page_size`

返回项建议统一为：

- `upload_id`
- `original_filename`
- `title`
- `source_ref`
- `file_ext`
- `file_size_bytes`
- `upload_status`
- `processing_stage`
- `report_id_ref`
- `retry_count`
- `updated_at`
- `created_at`

### 7.3 上传详情

```http
GET /api/uploads/{upload_id}
```

返回建议包含：

- 上传元数据
- 当前状态
- 错误信息
- 关联产物列表
- `report_id_ref`
- `report_detail_url`
- `raw_preview_available`

示例：

```json
{
  "upload_id": "upl_20260413_201530_a1b2c3d4",
  "original_filename": "karpathy_notes.pdf",
  "title": "Karpathy Notes",
  "source_ref": "upload://upl_20260413_201530_a1b2c3d4/karpathy_notes.pdf",
  "file_ext": "pdf",
  "file_size_bytes": 287133,
  "upload_status": "completed",
  "processing_stage": "done",
  "report_id_ref": "rpt_20260413_201641_9f6d1e2c",
  "compile_mode": "propose",
  "auto_compile": true,
  "retry_count": 0,
  "error_code": null,
  "error_message": null,
  "artifacts": [
    {
      "artifact_kind": "original_file",
      "file_path": "uploads/processed/2026/04/karpathy_notes.pdf"
    },
    {
      "artifact_kind": "extracted_text",
      "file_path": "raw/uploads/2026/04/upl_20260413_201530_a1b2c3d4.txt"
    },
    {
      "artifact_kind": "report_preview",
      "file_path": "reports/2026/04/rpt_20260413_201641_9f6d1e2c.md"
    }
  ],
  "created_at": "2026-04-13T20:15:30+08:00",
  "updated_at": "2026-04-13T20:16:45+08:00",
  "completed_at": "2026-04-13T20:16:45+08:00"
}
```

### 7.4 触发处理

```http
POST /api/uploads/{upload_id}/process
```

请求体：

```json
{
  "auto_compile": true,
  "compile_mode": "propose"
}
```

说明：

- 用于 `auto_process=false` 的手动启动。
- 已完成任务默认不可重复处理，需通过 `retry` 走显式重跑。

### 7.5 重试处理

```http
POST /api/uploads/{upload_id}/retry
```

请求体可选：

```json
{
  "from_stage": "extracting"
}
```

规则：

- 仅允许对 `failed` 或 `needs_review` 任务重试。
- 重试必须增加 `retry_count`。
- 若已有 `report_id_ref`，重试前必须定义是覆写原报告还是生成新报告。

MVP 建议：

- 默认生成新 `report_id`
- 旧 `report_id_ref` 保留在任务备注或扩展字段中
- 不对原报告静默覆盖

### 7.6 查看原始抽取内容

```http
GET /api/uploads/{upload_id}/raw
```

用途：

- 查看抽取文本
- 诊断 PDF/DOCX 抽取质量
- 支持人工审核

### 7.7 查看报告预览

```http
GET /api/uploads/{upload_id}/report-preview
```

用途：

- 在报告正式入库前预览 AI 生成结果
- 允许后续演进到“人工确认后再 sync”

---

## 8. 前端页面结构

### 8.1 新增页面

- `/uploads`
- `/uploads/:uploadId`

### 8.2 `Uploads` 列表页

展示字段：

- 文件名
- 标题
- 文件类型
- 文件大小
- 状态
- 处理阶段
- 是否已生成报告
- 更新时间

操作：

- 上传文件
- 按状态筛选
- 搜索文件名或标题
- 手动处理
- 重试
- 跳转关联报告

### 8.3 `Upload Detail` 详情页

建议布局：

- 左侧：原始文件信息、处理状态、错误信息、操作按钮
- 中间：抽取文本预览 / 报告预览切换
- 右侧：产物列表、关联报告、编译状态、诊断信息

建议操作：

- `Process`
- `Retry`
- `Open Report`
- `View Raw`
- `Compile`

### 8.4 与现有页面关系

- 上传成功后，可直接跳转 `/reports/{report_id}`
- 自动编译后，可在 `/tasks`、`/wiki`、`/conflicts` 中继续处理
- `Admin` 页可增加上传队列概览卡片

---

## 9. 与 openclaw Skill 的对接方式

### 9.1 角色划分

- openclaw Skill：适合处理 URL、网页、视频、外部来源抓取。
- Upload Center：适合处理用户本地文件、附件、离线资料。
- 两者最终都产出标准 `report`，然后汇入同一索引和知识编译体系。

### 9.2 统一入口策略

系统应同时支持两类 ingest：

- `skill_ingest`
- `upload_ingest`

统一落点：

- 标准报告文件
- `reports` 表
- `search_index`
- 可选 `wiki compile`

### 9.3 推荐接入原则

- 不要求 openclaw Skill 感知上传任务表结构。
- Upload Center 只需要复用现有报告元数据规范和后续 API。
- 若未来需要，Skill 也可以调用 `POST /api/uploads` 作为统一文件入口。

---

## 10. AI 处理策略

### 10.1 MVP 策略

首版建议分两层：

1. 抽取层：把文件稳定转成可读文本。
2. 总结层：把文本转成标准报告 Markdown。

首版不要在上传阶段直接做：

- 实体抽取写 Wiki
- 自动知识合并
- 多轮 Agent 互相协作编排

这些能力应继续留给现有：

- `/api/sync`
- `/api/wiki/compile`
- `/api/query/writeback`
- `/api/wiki/lint`

### 10.2 质量控制

建议增加最小质量门槛：

- 抽取文本长度过短时进入 `needs_review`
- 标题为空时回退到原文件名
- AI 输出缺失元数据时不允许直接 sync
- 报告正文为空时直接标记失败

### 10.3 Prompt 与产物追踪

建议保留这些中间产物：

- 抽取后的纯文本
- 送入模型的摘要输入
- 模型输出的原始文本
- 最终标准化报告预览

目的：

- 便于排查失败
- 便于优化 prompt
- 便于后续引入更强模型时做 A/B 对比

---

## 11. 检索与知识闭环影响

Upload Center 本身不直接解决检索，但它会扩大检索输入面。

形成闭环后：

1. 用户上传文件。
2. 文件生成标准报告。
3. 报告通过 `/api/sync` 进入 `search_index`。
4. 报告可通过 `/api/wiki/compile` 进入 `wiki_pages`。
5. 后续搜索、问答、写回、治理继续使用现有机制。

因此上传方案对“快速检索”的贡献是：

- 扩充高质量标准化报告供 FTS 建索引。
- 让离线资料也进入统一 `report -> wiki -> query` 通道。
- 为后续“越用越聪明”的知识闭环提供更多结构化输入。

---

## 12. MVP 验收标准

- 用户可通过前端或 API 上传 `txt/md/html/pdf/docx` 文件。
- 每次上传都会创建唯一 `upload_id`，且状态可追踪。
- 成功任务可生成标准 `report` 并获得 `report_id_ref`。
- 生成后的报告能在现有 `/api/reports` 与 `/app/#/reports/...` 中看到。
- 开启 `auto_compile` 时，上传生成的报告可进入现有 Wiki 编译链路。
- 失败任务能展示明确错误信息，并支持显式重试。
- 原始文件、抽取文本、报告预览至少能保留一种可审计产物。

---

## 13. 风险与注意事项

- PDF 和 DOCX 文本抽取质量波动较大，首版要接受 `needs_review` 分支。
- 不要让上传任务直接覆盖已有报告，否则会破坏审计链。
- 不要在上传阶段把太多 AI 决策前置，否则失败定位会很难。
- `source_ref` 必须保持为全链路主字段，不能因为上传来源而改成另一套命名。
- 上传文件可能包含敏感信息，后续应预留清理、脱敏、访问控制能力。

---

## 14. 推荐实施顺序

1. 先落表：`upload_jobs`、`upload_artifacts`
2. 再落目录：`uploads/inbox|working|processed|failed`
3. 实现 `POST /api/uploads` 与 `GET /api/uploads`
4. 实现单文件处理流水线与报告生成
5. 打通 `/api/sync`
6. 增加 `/uploads` 前端列表与详情页
7. 最后补 `auto_compile` 与人工审核入口

---

## 15. 结论

Upload Center MVP 最合理的定位不是“再造一个报告系统”，而是：

- 给现有系统增加文件上传型 ingest 入口
- 把上传文件稳定转成标准报告
- 让报告继续进入现有索引、编译、问答和治理闭环

这样扩展后，系统将同时具备：

- URL / 网页 / 视频型 ingest
- 本地文件 / 附件型 ingest
- 统一报告中心
- 统一知识编译入口
- 统一检索与治理能力

---

## 16. 拆分排期

本设计已进一步拆分为可执行排期文档，存放于：

- `plan_list/upload_center_mvp_design/00_plan_index.md`

建议后续直接按该目录下的阶段文档推进开发与验收。
