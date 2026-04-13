# Report Center MVP 设计方案

> 面向 openclaw Skill 生成的本地总结报告，构建一个可呈现、可管理、可查询的只读报告中心。  
> 目标是在不改变“报告落本地硬盘”这一前提下，为报告增加标准元数据、索引能力和 Web 可视化管理界面。

---

## 1. 目标与边界

### 1.1 MVP 目标

- 继续以本地磁盘文件作为报告内容的唯一权威数据源。
- 支持报告列表、详情阅读、全文搜索、筛选管理。
- 支持按时间、标签、来源域名、Skill 名称筛选。
- 支持报告索引重建和增量同步。
- 支持从 openclaw Skill 产出标准化报告文件并自动纳入索引。

### 1.2 非目标

- 不做在线编辑和回写文件。
- 不做多人权限和协同编辑。
- 不做复杂工作流编排平台。
- 不做分布式部署和远程数据库。
- 不在首版中接入向量库或 RAG 问答。

### 1.3 设计原则

- 文件系统存正文，数据库存索引和派生数据。
- 所有页面和 API 均以 `report_id` 与 `file_path` 双标识设计。
- 优先保证稳定读取、准确检索、低改造成本。
- 先做“能管理”，再做“更智能”。

---

## 2. 整体架构

```text
+--------------------------------------------------------------+
| Frontend (Vue3 + Vite)                                       |
| ReportList  Filters  Search  ReportDetail  Admin             |
+------------------------------+-------------------------------+
                               | HTTP/JSON
+------------------------------v-------------------------------+
| Backend (FastAPI)                                            |
| Report API  Search API  Tag API  Admin API  Sync Service     |
+------------------------------+-------------------------------+
                               |
+--------------------+---------+-------------------------------+
| File System        | SQLite / FTS5                           |
| reports/*.md       | reports.db                              |
| assets/            | reports, tags, search_index, sync_log   |
+--------------------+-----------------------------------------+
                               ^
                               |
                     openclaw Skill 输出报告
```

### 2.1 技术建议

- 后端：FastAPI
- 前端：Vue 3 + Vite + Naive UI
- 存储：本地 Markdown 文件
- 索引：SQLite + FTS5
- Markdown 渲染：markdown-it
- 代码高亮：highlight.js

### 2.2 为什么不把正文直接放数据库

- 你已经有 Skill 直接产出文件，改造成本最低。
- 本地文件方便备份、迁移、Git 管理和人工排查。
- SQLite 更适合保存检索索引，而不是承担“正文唯一存储”职责。

---

## 3. 目录结构

建议将报告中心根目录与 Skill 输出目录统一管理：

```text
report-center/
├─ reports/
│  ├─ 2026/
│  │  ├─ 04/
│  │  │  ├─ rpt_20260413_101523_xxx.md
│  │  │  └─ rpt_20260413_113015_xxx.md
│  │  └─ 05/
│  └─ failed/
├─ assets/
│  └─ images/
├─ data/
│  └─ reports.db
├─ backend/
│  └─ app/
├─ frontend/
│  └─ src/
└─ logs/
   └─ sync.log
```

### 3.1 文件命名建议

文件名建议包含时间戳和来源摘要，避免重名：

```text
rpt_YYYYMMDD_HHMMSS_<source_hash>.md
```

示例：

```text
rpt_20260413_101523_a1b2c3d4.md
```

### 3.2 路径规范

- 所有索引都使用相对于 `reports/` 的相对路径。
- 不允许上级目录穿越（`..` 路径段）。
- 报告附件路径也必须在 `report-center/` 根目录内。
- `file_service` 在读取任何文件前，必须校验解析后的绝对路径以 `reports/` 根目录为前缀，否则拒绝访问并返回 403。

---

## 4. 报告文件格式

推荐每篇报告使用 `Markdown + YAML front matter`：

```md
---
report_id: rpt_20260413_101523_a1b2c3d4
title: OpenClaw Skill 报告呈现方案总结
source_ref: https://example.com/article
source_url: https://example.com/article
source_domain: example.com
source_type: url
skill_name: link-summary
generated_at: 2026-04-13T10:15:23+08:00
author: openclaw
tags:
  - openclaw
  - report
  - product-design
status: published
language: zh-CN
summary: 关于本地报告中心建设方案的摘要。
content_hash: sha256:xxxx
related_urls:
  - https://example.com/article
  - https://example.com/reference
---

# OpenClaw Skill 报告呈现方案总结

正文内容...
```

### 4.1 必填字段

- `report_id`
- `title`
- `source_ref`：统一表示来源引用，可为 URL、文件路径、PDF 路径或其他来源标识
- `source_domain`（非 URL 来源时可填 `local` 或文件类型标识）
- `skill_name`
- `generated_at`
- `status`
- `summary`

> 实现约定：`source_ref` 是唯一的来源主字段；`source_url` 仅作为兼容字段保留。`source_type = url` 时两者通常相同；非 URL 来源时 `source_url` 可为空。

### 4.2 推荐字段

- `tags`
- `language`
- `content_hash`
- `related_urls`
- `author`
- `source_type`

### 4.3 `status` 建议枚举

- `published`
- `draft`
- `archived`
- `failed`

### 4.4 `content_hash` 规则

- 计算范围：**去掉 YAML front matter 后的正文部分**（即 `---` 第二个分隔符之后的内容）。
- 算法：SHA-256，十六进制小写，存储格式为 `sha256:<hex>`。
- Skill 写文件时计算并写入 front matter；`sync_service` 重新计算时使用相同范围，两者结果应一致。
- 若两者不一致，以 `sync_service` 重新计算的值为准，并触发更新。

### 4.5 `report_id` 规则

- 全局唯一。
- 一旦写入不再变更。
- 建议由时间戳 + `source_ref` hash 组成。

---

## 5. SQLite 表结构

SQLite 只保存元数据、检索索引和同步状态，不保存 Markdown 权威正文。

### 5.1 `reports`

```sql
CREATE TABLE reports (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id        TEXT NOT NULL UNIQUE,
    file_path        TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    source_ref       TEXT NOT NULL,
    source_url       TEXT,
    source_domain    TEXT NOT NULL,
    source_type      TEXT NOT NULL DEFAULT 'url',
    skill_name       TEXT NOT NULL,
    generated_at     TEXT NOT NULL,
    author           TEXT,
    status           TEXT NOT NULL DEFAULT 'published',
    language         TEXT,
    summary          TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    body_size        INTEGER NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

索引建议：

```sql
CREATE INDEX idx_reports_generated_at ON reports(generated_at DESC);
CREATE INDEX idx_reports_source_domain ON reports(source_domain);
CREATE INDEX idx_reports_skill_name ON reports(skill_name);
CREATE INDEX idx_reports_status ON reports(status);
```

### 5.2 `report_tags`

```sql
CREATE TABLE report_tags (
    report_id_ref    TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    tag              TEXT NOT NULL,
    normalized_tag   TEXT NOT NULL,
    PRIMARY KEY (report_id_ref, normalized_tag)
);

CREATE INDEX idx_report_tags_normalized_tag ON report_tags(normalized_tag);
```

### 5.3 `report_links`

用于记录报告关联的原始链接或正文中提取出的外链：

```sql
CREATE TABLE report_links (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id_ref    TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    url              TEXT NOT NULL,
    link_type        TEXT NOT NULL,
    anchor_text      TEXT,
    UNIQUE (report_id_ref, url, link_type)
);

CREATE INDEX idx_report_links_url ON report_links(url);
```

`link_type` 建议值：

- `source`
- `reference`
- `citation`
- `body_link`

### 5.4 `search_index`

使用 FTS5 构建全文检索：

```sql
CREATE VIRTUAL TABLE search_index USING fts5(
    report_id UNINDEXED,
    title,
    summary,
    body,
    tags,
    source_domain,
    skill_name,
    tokenize = 'unicode61'
);
```

> **中文分词限制：** `unicode61` 对中文按字符切分，不是词级别，搜索精度有限（如搜"知识库"可能无法精确匹配"知识"+"库"的组合）。MVP 阶段接受此限制。后续可在写入 FTS 前用 `jieba` 对中文字段做分词预处理，以空格分隔词语后再写入，届时将 `tokenize` 改回默认即可。

```sql
```

### 5.5 `sync_jobs`

记录同步和重建索引结果：

```sql
CREATE TABLE sync_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type         TEXT NOT NULL,
    mode             TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    scanned_count    INTEGER NOT NULL DEFAULT 0,
    created_count    INTEGER NOT NULL DEFAULT 0,
    updated_count    INTEGER NOT NULL DEFAULT 0,
    deleted_count    INTEGER NOT NULL DEFAULT 0,
    failed_count     INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL,
    message          TEXT
);
```

---

## 6. API 设计

所有 API 统一前缀为 `/api`。

### 6.1 报告列表

```http
GET /api/reports
```

查询参数：

- `q`：关键词
- `page`
- `page_size`
- `tag`
- `source_domain`
- `skill_name`
- `status`
- `date_from`
- `date_to`
- `sort_by=generated_at|title`
- `sort_order=desc|asc`

返回示例：

```json
{
  "items": [
    {
      "report_id": "rpt_20260413_101523_a1b2c3d4",
      "title": "OpenClaw Skill 报告呈现方案总结",
      "source_ref": "https://example.com/article",
      "source_url": "https://example.com/article",
      "source_domain": "example.com",
      "source_type": "url",
      "skill_name": "link-summary",
      "generated_at": "2026-04-13T10:15:23+08:00",
      "tags": ["openclaw", "report"],
      "status": "published",
      "summary": "关于本地报告中心建设方案的摘要。"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 135
}
```

### 6.2 报告详情

```http
GET /api/reports/{report_id}
```

返回内容：

- 元数据
- Markdown 正文
- 标签
- 外链
- 相邻报告或相关推荐

详情接口返回字段与列表接口保持一致，至少包含：

- `report_id`
- `title`
- `source_ref`
- `source_url`
- `source_domain`
- `source_type`
- `generated_at`
- `status`
- `summary`
- `content`

### 6.3 原始 Markdown

```http
GET /api/reports/{report_id}/raw
```

用于导出、调试和查看原始文件内容。

### 6.4 全文搜索

```http
GET /api/search?q=关键词
```

支持参数：

- `tag`
- `source_domain`
- `skill_name`
- `status`
- `limit`

返回示例：

```json
{
  "items": [
    {
      "report_id": "rpt_20260413_101523_a1b2c3d4",
      "title": "OpenClaw Skill 报告呈现方案总结",
      "snippet": "...本方案采用 <mark>SQLite</mark> + FTS5 实现全文检索...",
      "score": -3.82,
      "source_ref": "https://example.com/article",
      "source_domain": "example.com",
      "source_type": "url",
      "generated_at": "2026-04-13T10:15:23+08:00"
    }
  ],
  "total": 1,
  "took_ms": 5
}
```

### 6.5 标签聚合

```http
GET /api/tags
```

返回各标签及使用次数：

```json
{
  "items": [
    { "tag": "openclaw", "count": 42 },
    { "tag": "report", "count": 38 }
  ]
}
```

### 6.6 来源域名聚合

```http
GET /api/domains
```

用于前端筛选器快速加载来源站点列表。

### 6.7 同步接口

```http
POST /api/sync
```

请求体：

```json
{
  "mode": "incremental"
}
```

支持模式：

- `incremental`
- `full`

> **执行模式说明：** MVP 阶段同步为**同步执行**（请求阻塞直到完成后返回结果）。报告量小时延迟可接受。若报告量增大导致超时，后续可改为后台任务模式：接口立即返回 `job_id`，客户端轮询 `GET /api/sync/jobs/{job_id}` 查询进度。

返回示例：

```json
{
  "job_id": 18,
  "mode": "incremental",
  "scanned_count": 15,
  "created_count": 3,
  "updated_count": 2,
  "deleted_count": 0,
  "failed_count": 0,
  "status": "success",
  "took_ms": 146
}
```

### 6.8 健康检查

```http
GET /api/health
```

检查：

- 报告根目录是否存在
- SQLite 是否可读写
- 最近一次同步是否成功

### 6.9 失败报告列表

```http
GET /api/admin/failed-reports
```

用于管理端排查 front matter 缺失、文件损坏、解析失败等异常。

---

## 7. 前端页面结构

### 7.1 页面清单

| 页面 | 路由 | 说明 |
|------|------|------|
| 首页/列表页 | `/reports` | 报告列表、筛选、排序 |
| 详情页 | `/reports/:reportId` | 报告正文阅读与元数据展示 |
| 搜索页 | `/search` | 全文搜索结果列表 |
| 管理页 | `/admin` | 同步、重建索引、异常报告 |

### 7.2 列表页布局

建议三段布局：

- 左侧：筛选器
- 中间：报告列表
- 顶部：搜索框、排序、同步状态

筛选器建议包含：

- 时间范围
- 来源域名
- 标签
- Skill 名称
- 状态

列表项字段建议展示：

- 标题
- 短摘要
- 来源域名
- 生成时间
- 标签
- 状态

### 7.3 详情页布局

顶部信息区：

- 标题
- 来源 URL
- 来源域名
- Skill 名称
- 生成时间
- 标签
- 状态

正文区：

- Markdown 渲染结果
- 支持目录跳转
- 支持代码块高亮

右侧辅助区：

- 原始链接列表
- 相关报告
- 同标签报告
- 导出原文

### 7.4 搜索页

核心能力：

- 关键词输入
- 搜索结果高亮摘要
- 快速筛选域名和标签
- 点击结果跳详情页

### 7.5 管理页

建议包含：

- 最近同步结果
- 手动同步按钮
- 全量重建按钮
- 失败报告列表
- 重复来源 URL 报表
- 按域名、按 Skill 的统计卡片

---

## 8. 与 openclaw Skill 的对接方式

这是 MVP 成败的关键，建议最少改造 Skill 输出层，不改你现有的核心总结逻辑。

### 8.1 Skill 输出约定

Skill 每次成功生成报告后，必须完成两个动作：

1. 输出标准化 Markdown 报告文件到 `reports/YYYY/MM/`
2. 将 front matter 写完整

可选第三步：

3. 调用本地 `POST /api/sync` 触发一次增量同步

### 8.2 Skill 输出流程

```text
用户输入链接
  -> Skill 抓取内容
  -> Skill 生成总结
  -> 计算 source_ref / source_domain / report_id / content_hash
  -> 组装 front matter
  -> 写入 markdown 文件
  -> 调用 /api/sync?mode=incremental
  -> 前端即可看到新报告
```

### 8.3 Skill 写文件时必须保证

- 使用 UTF-8 编码。
- `generated_at` 为标准 ISO 8601 时间。
- `report_id` 全局唯一。
- `summary` 为短摘要，便于列表页展示。
- `tags` 始终输出数组，即使只有一个值。

### 8.4 Skill 对接的两种实现方式

#### 方式 A：文件落地后由后端扫描

- Skill 只负责写文件。
- 后端定时或手动增量同步。
- 最稳定，耦合最低。

适用：

- 你先求稳，不急着做自动刷新。

#### 方式 B：Skill 写文件后主动调用后端接口

- Skill 写完文件立刻请求 `POST /api/sync`
- 前端几乎实时可见

适用：

- 你希望“生成完就出现在界面里”

MVP 建议先上方式 A，随后补方式 B。

### 8.5 Skill 输出失败时的建议

当抓取失败、总结失败、写文件失败时：

- 记录错误日志
- 可选写入 `reports/failed/` 下的错误记录文件
- 或写入 `sync_jobs/message`

不要把“失败报告”混入正常报告目录。

---

## 9. 后端实现拆分建议

### 9.1 模块划分

```text
backend/app/
├─ main.py
├─ config.py
├─ db.py
├─ routers/
│  ├─ reports.py
│  ├─ search.py
│  ├─ taxonomy.py
│  ├─ admin.py
│  └─ health.py
├─ services/
│  ├─ report_service.py
│  ├─ search_service.py
│  ├─ sync_service.py
│  ├─ metadata_service.py
│  └─ file_service.py
├─ indexing/
│  ├─ frontmatter.py
│  ├─ markdown_parser.py
│  ├─ fts.py
│  └─ scanner.py
└─ schemas/
   ├─ report.py
   ├─ search.py
   ├─ admin.py
   └─ sync.py
```

### 9.2 核心服务职责

- `file_service`：读取原始 Markdown 文件
- `metadata_service`：解析 front matter、提取摘要和标签
- `sync_service`：扫描目录、增量同步、更新索引
- `search_service`：执行 FTS 查询和结果高亮
- `report_service`：聚合详情页数据

---

## 10. 增量同步策略

### 10.1 扫描依据

每个文件计算：

- `file_path`
- `mtime`
- `size`
- `content_hash`

### 10.2 判定规则

- 文件存在于磁盘、不存在于数据库：新增
- 文件存在于两边，但 `content_hash` 不同：更新
- 文件存在于数据库、不存在于磁盘：删除

### 10.3 增量同步流程

```text
1. 扫描 reports/ 下所有 .md 文件
2. 解析 front matter 和正文
3. 计算内容 hash
4. 对比数据库记录
5. 更新 reports / report_tags / report_links / search_index
6. 写入 sync_jobs
```

### 10.4 全量重建触发时机

- front matter 规范变更
- FTS schema 变更
- 报告目录迁移
- 数据明显异常时

---

## 11. MVP 交付顺序

### Phase 1：后端基础

- 建立 SQLite schema
- 实现报告扫描与解析
- 实现 `/api/health`
- 实现 `/api/reports`
- 实现 `/api/reports/{report_id}`

### Phase 2：搜索与管理

- 实现 FTS5 检索
- 实现 `/api/search`
- 实现 `/api/tags` 和 `/api/domains`
- 实现 `/api/sync`

### Phase 3：前端阅读器

- 列表页
- 详情页
- 搜索页
- 基础管理页

### Phase 4：Skill 对接自动化

- Skill 统一 front matter 输出
- Skill 生成后主动触发增量同步

---

## 12. 首版验收标准

- 新报告写入 `reports/` 后能被系统识别。
- 列表页可按时间倒序查看报告。
- 可以按关键词进行全文搜索。
- 可以按标签、域名、Skill 名称筛选。
- 点进详情页能看到 Markdown 正文和来源链接。
- 同步接口能正确识别新增、更新、删除。
- 异常文件不会阻塞整体同步。

---

## 13. 后续增强方向

- 相似报告推荐
- 重复链接检测
- 按来源站点统计
- 周报汇总视图
- 报告图谱关系视图
- Git 历史版本回溯
- 向量检索与问答

---

## 14. 实施结论

对你当前场景，推荐的最小可用方案是：

- 保持 openclaw Skill 输出 Markdown 到本地磁盘
- 为每篇报告补齐 front matter 元数据
- 用 FastAPI + SQLite FTS5 建立索引和查询接口
- 用 Vue3 做列表、搜索、详情、管理四个页面

这条路线的优点是：

- 不推翻你现有 Skill
- 开发量可控
- 扩展路径清晰
- 本地单机场景足够稳定

如果后续要继续推进实现，下一步最合适的是直接进入：

1. `schema.sql`
2. `sync_service.py`
3. `GET /api/reports`
4. 前端列表页骨架
