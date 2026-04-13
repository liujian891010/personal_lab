# Report Center + LLM Wiki V2 设计方案

> 在 `Report Center MVP` 的基础上，引入 Knowledge Compilation 思路，将“报告中心”升级为“会持续编译、更新、整理、回答问题”的个人知识库系统。  
> 本方案遵循 `report -> wiki -> query -> lint -> writeback` 的闭环，而不是把系统停留在“只会存报告和搜报告”的阶段。

相关基础文档：

- [REPORT_CENTER_MVP_DESIGN.md](./REPORT_CENTER_MVP_DESIGN.md)

---

## 1. V2 目标

### 1.1 核心目标

- 保留本地报告文件作为原始知识快照。
- 在报告之上增加可持续演化的 `Wiki` 知识层。
- 让系统支持 `Ingest`、`Query`、`Lint` 三类智能循环。
- 让高价值问答和整理结果能回写为知识页，而不是停留在一次性对话。
- 让知识库越用越完整、越查越准、越问越像“懂你自己的资料”。

### 1.2 V2 与 MVP 的差异

MVP 解决：

- 报告保存
- 报告管理
- 报告检索
- 报告阅读

V2 新增：

- 知识页编译
- 实体/概念/问题/时间线组织
- 知识冲突与待办治理
- 问答回写
- 混合检索与答案合成

### 1.3 非目标

- 不训练私有模型。
- 不让 AI 无边界自动改写所有知识页。
- 不做完全无人审核的“自演化代理”。
- 不在首版中引入复杂多智能体编排平台。

---

## 2. 核心理念

### 2.1 四层结构

```text
Layer 0: Raw
  原始网页、转写、截图、PDF、附件

Layer 1: Reports
  openclaw Skill 生成的总结报告

Layer 2: Wiki
  面向实体、概念、问题、主题、时间线的知识页

Layer 3: Schema & Governance
  编译规则、冲突规则、任务队列、审核机制
```

### 2.2 设计原则

- `报告` 是快照，不是最终知识形态。
- `Wiki` 是持续整理后的活体知识。
- `问答` 不是终点，重要答案应回写成知识。
- `冲突` 不应被覆盖隐藏，而应显式管理。
- `AI` 负责提炼、关联、建议更新；`人` 负责裁决和治理。

---

## 3. 整体架构

```text
+----------------------------------------------------------------+
| Frontend                                                       |
| Reports | Wiki | Search | Ask | Tasks | Conflicts | Admin      |
+-----------------------------------+----------------------------+
                                    | HTTP/JSON
+-----------------------------------v----------------------------+
| Backend                                                        |
| Report APIs | Wiki APIs | Query APIs | Lint APIs | Sync APIs   |
| Compilation Service | Search Service | Governance Service      |
+-------------------------+--------------------+-----------------+
                          |                    |
+-------------------------v--+      +---------v------------------+
| File System                |      | SQLite / FTS / Optional Vec |
| raw/ reports/ knowledge/   |      | reports + wiki + tasks      |
+----------------------------+      +-----------------------------+
                          ^
                          |
                   openclaw Skills / Batch Jobs
```

### 3.1 最重要的升级点

- 报告不再是终点，而是知识编译输入。
- 系统同时维护 `报告索引` 和 `知识索引`。
- 搜索优先命中 `Wiki`，再回退到 `Reports`。
- 问答使用“知识页 + 报告证据”的双层上下文。

---

## 4. 目录结构

建议在现有 `report-center/` 下扩展：

```text
report-center/
├─ raw/
│  ├─ 2026/
│  │  └─ 04/
│  │     ├─ src_20260413_xxx.html
│  │     ├─ src_20260413_xxx.json
│  │     └─ assets/
├─ reports/
│  ├─ 2026/
│  │  └─ 04/
│  │     └─ rpt_20260413_101523_a1b2c3d4.md
│  └─ failed/
├─ knowledge/
│  ├─ entities/
│  ├─ concepts/
│  ├─ topics/
│  ├─ questions/
│  ├─ timelines/
│  ├─ conflicts/
│  ├─ digests/
│  └─ index.md
├─ prompts/
│  ├─ compile/
│  ├─ query/
│  └─ lint/
├─ data/
│  └─ reports.db
├─ backend/
├─ frontend/
└─ logs/
```

### 4.1 各目录职责

- `raw/`：保存抓取原文、转写、结构化抓取结果。
- `reports/`：保存每次 Skill 的总结报告。
- `knowledge/`：保存整理后的知识页。
- `conflicts/`：保存冲突记录，避免被静默覆盖。
- `digests/`：保存周报、专题汇总、阶段性摘要。

---

## 5. 知识页模型

### 5.1 知识页类型

建议 V2 至少支持 5 类页面：

- `entity`
- `concept`
- `topic`
- `question`
- `timeline`

### 5.2 页面职责

- `entity`：人、公司、项目、产品、组织
- `concept`：术语、方法论、架构模式
- `topic`：围绕某一主题的综合整理页
- `question`：针对一个高频问题的稳定答案页
- `timeline`：同一主题的时间演化页

### 5.3 知识页文件示例

```md
---
page_id: pg_entity_openclaw
page_type: entity
title: OpenClaw
slug: openclaw
status: active
created_at: 2026-04-13T12:00:00+08:00
updated_at: 2026-04-13T12:00:00+08:00
source_report_ids:
  - rpt_20260413_101523_a1b2c3d4
tags:
  - agent
  - workflow
confidence: 0.83
---

# OpenClaw

## Overview

一句话概述。

## Key Facts

- ...

## Related Concepts

- [[agentic-workflow]]
- [[report-center]]

## Evidence

- [[rpt_20260413_101523_a1b2c3d4]]
```

### 5.4 页面元数据建议

- `page_id`
- `page_type`
- `title`
- `slug`
- `status`
- `created_at`
- `updated_at`
- `source_report_ids`
- `tags`
- `confidence`

### 5.5 `slug` 生成规则

- 英文标题：小写 + 空格替换为 `-`，去除特殊字符。
- 中文标题：使用 `pypinyin` 转拼音后按上述规则处理，截断至 64 字符。
- 若转换后冲突，追加 `_2`、`_3` 等后缀。
- 示例：`OpenClaw` → `openclaw`，`知识库` → `zhi-shi-ku`。
- `slug` 一旦生成不建议变更（影响外部链接），如需变更应在旧 slug 上保留重定向记录。

### 5.6 `confidence` 计算规则

MVP 阶段采用规则打分，不依赖模型判断：

| 条件 | 分值 |
|------|------|
| 每增加一个支撑报告（上限 3 个） | +0.15 |
| 最近 30 天内有更新 | +0.1 |
| 无冲突记录 | +0.2 |
| 有冲突记录（status=open） | -0.3 |
| 基础分 | 0.4 |

最终值 clamp 到 `[0.0, 1.0]`。显示规则沿用文档第 15.3 节阈值（0.8+ / 0.5-0.8 / <0.5）。

### 5.7 页面状态建议

- `active`
- `draft`
- `needs_review`
- `deprecated`
- `conflicted`

---

## 6. 数据库设计

V2 继续复用 MVP 的 `reports` 相关表，并新增知识编译层表结构。

### 6.1 `wiki_pages`

```sql
CREATE TABLE wiki_pages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id          TEXT NOT NULL UNIQUE,
    page_type        TEXT NOT NULL,
    file_path        TEXT NOT NULL UNIQUE,
    slug             TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'active',
    summary          TEXT,
    confidence       REAL,
    content_hash     TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

索引建议：

```sql
CREATE INDEX idx_wiki_pages_page_type ON wiki_pages(page_type);
CREATE INDEX idx_wiki_pages_status ON wiki_pages(status);
CREATE INDEX idx_wiki_pages_updated_at ON wiki_pages(updated_at DESC);
```

> `slug` 作为 `/api/wiki/by-slug/{slug}` 和前端 `/wiki/:slug` 的稳定访问键，必须全局唯一。

### 6.2 `wiki_page_tags`

```sql
CREATE TABLE wiki_page_tags (
    page_id_ref      TEXT NOT NULL REFERENCES wiki_pages(page_id) ON DELETE CASCADE,
    tag              TEXT NOT NULL,
    normalized_tag   TEXT NOT NULL,
    PRIMARY KEY (page_id_ref, normalized_tag)
);
```

### 6.3 `wiki_links`

表示知识页之间、知识页到报告之间的关系。

```sql
CREATE TABLE wiki_links (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id   TEXT NOT NULL,
    target_kind      TEXT NOT NULL,
    target_id        TEXT NOT NULL,
    link_type        TEXT NOT NULL,
    anchor_text      TEXT,
    is_resolved      INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_wiki_links_source ON wiki_links(source_page_id);
CREATE INDEX idx_wiki_links_target ON wiki_links(target_kind, target_id);
```

字段说明：

- `target_kind`：`wiki_page` | `report`
- `link_type`：`related` | `supports` | `contradicts` | `mentions`

### 6.4 `page_sources`

表示某知识页由哪些报告支撑。

```sql
CREATE TABLE page_sources (
    page_id_ref      TEXT NOT NULL REFERENCES wiki_pages(page_id) ON DELETE CASCADE,
    report_id_ref    TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    evidence_role    TEXT NOT NULL,
    PRIMARY KEY (page_id_ref, report_id_ref, evidence_role)
);
```

`evidence_role` 建议值：

- `primary`
- `secondary`
- `historical`
- `conflicting`

### 6.5 `knowledge_tasks`

这张表是“越用越聪明”的核心治理表。

```sql
CREATE TABLE knowledge_tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type        TEXT NOT NULL,
    target_kind      TEXT NOT NULL,
    target_id        TEXT,
    title            TEXT NOT NULL,
    description      TEXT,
    priority         TEXT NOT NULL DEFAULT 'medium',
    status           TEXT NOT NULL DEFAULT 'open',
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

`task_type` 建议值：

- `compile_page`
- `update_page`
- `resolve_conflict`
- `merge_duplicate`
- `fill_gap`
- `review_answer_writeback`

### 6.6 `knowledge_conflicts`

```sql
CREATE TABLE knowledge_conflicts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_key        TEXT NOT NULL,
    page_id_ref      TEXT,
    old_claim        TEXT NOT NULL,
    new_claim        TEXT NOT NULL,
    evidence_report_id TEXT,
    severity         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'open',
    created_at       TEXT NOT NULL,
    resolved_at      TEXT
);
```

### 6.7 `question_runs`

记录用户问答与回写结果。

```sql
CREATE TABLE question_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text    TEXT NOT NULL,
    answer_summary   TEXT,
    wrote_back_page_id TEXT,
    created_at       TEXT NOT NULL
);

-- 拆出关联表，避免用 TEXT 存 ID 数组，便于查询
CREATE TABLE question_run_sources (
    run_id           INTEGER NOT NULL REFERENCES question_runs(id) ON DELETE CASCADE,
    source_kind      TEXT NOT NULL,  -- 'wiki_page' | 'report'
    source_id        TEXT NOT NULL,
    PRIMARY KEY (run_id, source_kind, source_id)
);

CREATE INDEX idx_qrun_sources_run ON question_run_sources(run_id);
CREATE INDEX idx_qrun_sources_source ON question_run_sources(source_kind, source_id);
```

### 6.8 知识搜索索引

对 `Wiki` 和 `Report` 分别建 FTS 表，避免混在一起难调权重。

```sql
CREATE VIRTUAL TABLE wiki_search_index USING fts5(
    page_id UNINDEXED,
    title,
    summary,
    body,
    tags,
    page_type,
    tokenize = 'unicode61'
);
```

### 6.9 混合检索策略

V2 建议采用：

- 第一阶段：`SQLite B-Tree + FTS5`
- 第二阶段：`FTS5 + optional vector recall`
- 第三阶段：`BM25 + vector + rerank`

不要一开始就上向量库。你的系统当前最缺的不是向量检索，而是稳定的知识编译与治理。

---

## 7. 核心工作流

V2 的核心不是页面，而是 3 个循环。

### 7.1 Ingest

目标：把新报告转成结构化知识增量。

流程：

```text
新链接
-> raw 抓取
-> 生成 report
-> report 入库
-> 编译器提取 entity / concept / topic / claim
-> 生成知识更新提案
-> 落地 wiki page 或待审核任务
-> 更新 wiki 索引
```

#### Ingest 输出

- 新增报告
- 新建或更新知识页
- 新增页面链接
- 新增冲突记录
- 新增待处理任务

### 7.2 Query

目标：让问答优先基于稳定知识，而不是每次现读所有报告。

流程：

```text
用户提问
-> 问题归一化
-> 召回 wiki pages
-> 不足时补召回 reports
-> 组装证据
-> 生成回答
-> 评估是否值得回写
-> 如值得，生成 question page 或 update task
```

#### Query 的输出层级

- 第一层：直接答案
- 第二层：引用的知识页和报告证据
- 第三层：是否回写为长期知识

### 7.3 Lint

目标：让知识库不是越堆越乱，而是越积越清晰。

Lint 周期任务建议检查：

- 高频被引用却没有页面的概念
- 多页重复表达同一主题
- 长时间未更新但仍高频命中的页面
- 存在冲突的页面
- 孤儿页
- 失效外链
- 引用已删除报告的知识页

#### Lint 输出

- `knowledge_tasks`
- `knowledge_conflicts`
- `digests/` 周报

---

## 8. 编译策略

### 8.1 从报告中提取什么

V2 不是把整篇报告复制成 wiki，而是提取这些结构：

- 实体
- 概念
- 关键结论
- 事实声明
- 数据点
- 时间线事件
- 未决问题
- 与已有知识的冲突点

### 8.2 何时新建页面

满足以下任一条件时可新建：

- 新实体首次出现且重要性高
- 新概念被多个报告重复提及
- 某问题被多次追问
- 某专题已有 3 篇以上相关报告

### 8.3 何时更新页面

- 仅增加新证据
- 新报告改变了关键事实
- 新增了相关页面链接
- 需要补充时间线

### 8.4 何时不自动更新

- 会改写已有结论的核心表述
- 存在明显冲突
- 需要删除大量旧内容
- 证据不足但模型推断很强

这类情况应写成：

- `knowledge_tasks`
- `knowledge_conflicts`

而不是直接自动覆盖。

---

## 9. Query 检索与回答设计

### 9.1 检索顺序

V2 建议固定为：

```text
1. 先查 wiki_pages
2. 对 `page_type = question` 的命中结果做权重提升
3. 不足时回退到 reports
4. 如仍不足，再提示需要新 ingest
```

### 9.2 召回策略

- 元数据筛选：按标签、页面类型、更新时间
- FTS：查 `wiki_search_index`
- 报告补召回：查 `search_index`
- 可选 rerank：按问题与证据相关性排序

### 9.3 回答模板建议

每次回答尽量输出：

- 结论
- 依据
- 不确定点
- 建议下一步

### 9.4 何时回写

以下问答值得写回：

- 用户重复问到的问题
- 长答案且证据充分
- 可抽象成稳定 FAQ 的问题
- 对现有知识页形成补充的答案

回写落点：

- `knowledge/questions/`
- 对应 `topic` 或 `entity` 页面更新

---

## 10. 前端设计

V2 前端不再只是“报告阅读器”，而是“知识工作台”。

### 10.1 页面结构

| 页面 | 路由 | 说明 |
|------|------|------|
| 报告中心 | `/reports` | 保留 MVP 报告列表与详情 |
| 知识页 | `/wiki/:slug` | 展示实体/概念/专题/问题页 |
| 知识导航 | `/wiki` | 按类型浏览知识页 |
| 问答台 | `/ask` | 基于 wiki + reports 回答问题 |
| 冲突中心 | `/conflicts` | 查看冲突与待裁决项 |
| 治理任务 | `/tasks` | 查看 lint 生成的任务 |
| 管理台 | `/admin` | 同步、重建索引、编译状态 |

### 10.2 知识页详情布局

顶部：

- 页面标题
- 类型
- 置信度
- 最后更新时间
- 来源报告数量

正文区：

- Markdown 渲染
- 页面内目录

右侧侧栏：

- 相关知识页
- 支撑证据报告
- 冲突提醒
- 最近变更

### 10.3 问答台

输入问题后返回：

- 结论答案
- 主要证据页
- 支撑报告
- 回写建议按钮

### 10.4 治理视图

应优先做这 3 个卡片：

- 待编译页面
- 待解决冲突
- 高频提问未沉淀

---

## 11. API 设计

V2 在 MVP API 之上新增 Wiki、Query、Lint 三组接口。

### 11.1 Wiki 页面列表

```http
GET /api/wiki/pages
```

参数：

- `page_type`
- `tag`
- `status`
- `q`
- `page`
- `page_size`

### 11.2 Wiki 页面详情

```http
GET /api/wiki/pages/{page_id}
```

返回：

- 页面元数据
- Markdown 正文
- 支撑报告
- 相关知识页
- 冲突摘要

### 11.3 按 slug 访问知识页

```http
GET /api/wiki/by-slug/{slug}
```

### 11.4 触发编译

```http
POST /api/wiki/compile
```

请求体：

```json
{
  "report_id": "rpt_20260413_101523_a1b2c3d4",
  "mode": "propose"
}
```

`mode`：

- `propose`：仅生成编译提案，写入 `knowledge_tasks`，不自动落地知识页，需人工审核。
- `apply_safe`：自动应用第 15.1 节定义的安全更新，其余变更仍写入 `knowledge_tasks`。

**触发来源说明：**

| 来源 | 行为 |
|------|------|
| Skill 写报告后主动调用 | 传入 `report_id`，针对单篇报告编译 |
| 前端管理台手动触发 | 传入 `report_id` 或不传（批量处理未编译报告） |
| 批量任务（后台定时） | 不传 `report_id`，扫描所有 `knowledge_tasks` 中 `compile_page` 类型的待办 |

手动触发与自动触发行为一致，区别仅在于调用方。`report_id` 为空时，后端依次处理队列中待编译的报告。

### 11.5 问答接口

```http
POST /api/query/ask
```

请求体：

```json
{
  "question": "openclaw 的报告系统如何升级成 LLM Wiki？",
  "writeback": "suggest"
}
```

返回：

- 答案
- source wiki pages
- source reports
- 是否建议回写

### 11.6 回写接口

```http
POST /api/query/writeback
```

用于把一次问答沉淀为：

- question page
- topic page update
- task item

### 11.7 冲突列表

```http
GET /api/wiki/conflicts
```

### 11.8 任务列表

```http
GET /api/wiki/tasks
```

### 11.9 运行 lint

```http
POST /api/wiki/lint
```

支持模式：

- `light`
- `full`

---

## 12. LLM 接入设计

### 12.1 模型选择

- 默认使用 Claude API（`claude-sonnet-4-6` 或更新版本）。
- 通过环境变量 `LLM_MODEL` 配置，便于切换。

### 12.2 调用封装

所有 LLM 调用统一通过 `services/llm_service.py` 封装，不在业务服务中直接调用 SDK：

```python
# services/llm_service.py
class LLMService:
    def complete(self, prompt_key: str, variables: dict) -> str:
        """加载 prompt 模板，填充变量，调用模型，返回文本结果。"""
        ...
```

### 12.3 Prompt 管理

Prompt 模板存放在 `prompts/` 目录，按用途分子目录：

```text
prompts/
├─ compile/
│  ├─ extract_entities.md
│  ├─ extract_concepts.md
│  └─ generate_page_proposal.md
├─ query/
│  ├─ answer_with_context.md
│  └─ evaluate_writeback.md
└─ lint/
   └─ detect_conflicts.md
```

每个模板为 Markdown 文件，使用 `{{variable}}` 占位符，由 `llm_service` 在调用前渲染。

### 12.4 调用时机

| 功能 | 触发接口 | Prompt |
|------|----------|--------|
| 编译报告为知识提案 | `POST /api/wiki/compile` | `compile/extract_entities.md` 等 |
| 问答 | `POST /api/query/ask` | `query/answer_with_context.md` |
| 评估是否回写 | 问答后自动 | `query/evaluate_writeback.md` |
| Lint 冲突检测 | `POST /api/wiki/lint` | `lint/detect_conflicts.md` |

### 12.5 注意事项

- LLM 调用结果不直接写入知识页，必须经过 `propose` → 审核 → `apply` 流程。
- 调用失败时写入 `knowledge_tasks`（`task_type=compile_page`，`status=open`），不阻塞主流程。
- API Key 通过环境变量 `ANTHROPIC_API_KEY` 注入，不写入代码或配置文件。

---

## 13. 后端模块拆分（原第 12 节）

```text
backend/app/
├─ routers/
│  ├─ reports.py
│  ├─ wiki.py
│  ├─ query.py
│  ├─ governance.py
│  └─ admin.py
├─ services/
│  ├─ report_service.py
│  ├─ wiki_service.py
│  ├─ compile_service.py
│  ├─ query_service.py
│  ├─ lint_service.py
│  ├─ task_service.py
│  └─ conflict_service.py
├─ indexing/
│  ├─ report_indexer.py
│  ├─ wiki_indexer.py
│  ├─ entity_extractor.py
│  ├─ concept_extractor.py
│  └─ link_resolver.py
└─ schemas/
   ├─ wiki.py
   ├─ query.py
   ├─ task.py
   └─ conflict.py
```

### 13.1 新服务职责

- `compile_service`：把报告编译为知识提案或安全更新
- `wiki_service`：管理知识页读写与关系聚合
- `query_service`：执行召回、证据拼装和回答
- `lint_service`：运行体检规则并生成治理任务
- `task_service`：管理待办、审核、完成状态
- `conflict_service`：管理冲突记录与合并决策

---

## 14. openclaw Skill 对接

V2 不要求 Skill 直接维护整套 wiki。Skill 只需做到“稳定产出报告 + 可选触发编译”。

### 14.1 Skill 输出动作

1. 抓取原始内容到 `raw/`
2. 生成报告到 `reports/`
3. 调用 `/api/sync`
4. 可选调用 `/api/wiki/compile`

### 14.2 推荐的责任边界

- Skill：负责抓取、总结、落报告
- 后端编译器：负责抽取实体、概念、证据和知识页更新
- 前端治理台：负责审核、冲突解决、人工介入

### 14.3 自动化级别建议

首版建议分 3 档：

- `Level 1`
  Skill 写报告，人工点“编译”

- `Level 2`
  Skill 写报告后自动生成编译提案，人工审核落地

- `Level 3`
  对低风险知识页自动应用安全更新，对高风险更新保留审核

建议从 `Level 2` 开始，不建议直接上 `Level 3`。

---

## 15. 治理规则

### 15.1 自动可应用的安全更新

- 仅追加来源报告引用
- 仅补充相关链接
- 仅补充不冲突的事实列表
- 仅更新统计数字或时间线尾部事件，且证据明确

### 15.2 必须人工审核的变更

- 改写页面摘要
- 替换关键结论
- 解决冲突
- 合并两个页面
- 删除大量内容

### 15.3 置信度规则

建议知识页维护 `confidence`：

- `0.8+`：多来源、无冲突、近期更新
- `0.5-0.8`：来源有限但基本可信
- `<0.5`：只是一条线索或推测，应显式标注

---

## 16. 实施阶段

### Phase 1：在 MVP 上加 Wiki 底座

- 建 `wiki_pages`
- 建 `page_sources`
- 建 `wiki_search_index`
- 做 `/api/wiki/pages`

### Phase 2：做编译链路

- 从 report 抽取实体和概念
- 生成 `entity` 和 `concept` 页面
- 支持编译提案

### Phase 3：做 Query 闭环

- `POST /api/query/ask`
- 优先 wiki、回退 reports
- 返回证据链

### Phase 4：做 Lint 和治理

- 生成 `knowledge_tasks`
- 生成 `knowledge_conflicts`
- 上前端治理视图

### Phase 5：做回写

- 把高价值问答沉淀为 `question` 页面
- 对已有知识页做补充更新

---

## 17. 验收标准

- 一篇新报告进入后，系统可以自动识别相关实体或概念。
- 重要知识可沉淀为 `Wiki` 页面，而不是停留在报告层。
- 问答时优先引用知识页，并能回溯到支撑报告。
- 冲突信息不会被静默覆盖，而会进入冲突中心。
- Lint 可稳定发现孤儿页、重复页、待补全主题。
- 高频问题能沉淀为 `question` 页面。

---

## 18. 实施结论

V2 的本质不是“给报告中心加个聊天框”，而是把系统变成：

- 有原始资料层
- 有报告快照层
- 有知识编译层
- 有问答和治理闭环

对你当前场景，最合理的演进路线是：

1. 继续保留 MVP 的 `Report Center`
2. 新增 `knowledge/` 和 `wiki_pages`
3. 先做 `entity / concept` 两类知识页
4. 再做 `query -> writeback`
5. 最后做 `lint -> tasks -> conflicts`

这样可以在不推翻现有 Skill 的前提下，把系统升级成一个真正可持续演化的个人知识库。
