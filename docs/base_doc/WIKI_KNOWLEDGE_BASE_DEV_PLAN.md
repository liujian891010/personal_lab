# Wiki 知识库系统 - 可实施开发方案

> 面向 `arc-reactor-doc/wiki/` 的只读可视化知识库。目标是先做出一个稳定、可运行、可扩展的 MVP，再逐步增加图谱、标签和智能能力。

---

## 1. 文档目标

本文档用于约束 MVP 的实现边界，解决以下几个问题：

- 明确唯一数据源和文件标识，避免路径和命名歧义。
- 明确 SQLite 只承担元数据、链接关系和搜索索引职责，不作为权威内容存储。
- 明确 WikiLink 的支持范围、解析规则和歧义处理。
- 明确 API、前端路由和同步流程，保证前后端能独立开发并顺利联调。

---

## 2. 范围定义

### 2.1 MVP 目标

- 以 `arc-reactor-doc/wiki/` 作为唯一数据源读取 Markdown 文件。
- 提供目录树、Markdown 阅读、WikiLink 跳转、反向链接、全文搜索、基础图谱。
- 支持手动同步索引，保证文件新增、修改、删除后可重新检索。
- 支持中文内容搜索和基础标签聚合。

### 2.2 非目标

- 不提供在线编辑和回写文件能力。
- 不提供权限系统、用户系统、多租户能力。
- 不做实时文件监听和自动热同步。
- 不做分布式部署和远程数据库。
- 不集成 LLM 问答流程到首版 MVP。

---

## 3. 核心约定

### 3.1 唯一数据源

- 知识库根目录固定为 `arc-reactor-doc/wiki/`。
- 所有 Markdown 文件都必须位于该目录下或其子目录中。
- 磁盘上的 Markdown 文件是唯一权威数据源。
- SQLite 中允许保存索引和派生数据，但这些数据都可以从文件系统重新构建。

### 3.2 文件唯一标识

- 文件的唯一标识为相对于 `arc-reactor-doc/wiki/` 的相对路径，包含扩展名 `.md`。
- 示例：
  - `entities/karpathy.md`
  - `sources/youtube-abc.md`
  - `index.md`
- `basename` 和 `title` 仅用于展示和链接解析辅助，不能作为唯一主键。

### 3.3 路径规范

- 后端 API 中所有文件路径参数都使用相对路径。
- FastAPI 路由统一采用 `{file_path:path}` 形式接收多级目录路径。
- 前端路由统一采用 Vue Router 的 catch-all 形式接收多级目录路径。
- 所有路径在进入业务逻辑前都必须做规范化处理：
  - 拒绝绝对路径。
  - 拒绝包含 `..` 的路径穿越。
  - 解析真实路径后必须仍位于 `arc-reactor-doc/wiki/` 根目录下。

### 3.4 SQLite 职责

- `SQLite` 用于保存以下数据：
  - 文件元数据
  - 标题和标签
  - 解析后的 heading 信息
  - 出站链接关系
  - 全文搜索索引
- `SQLite` 不保存“权威版本”的 Markdown 文件，不参与内容编辑。

---

## 4. 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vue3 + Vite)                  │
│  FileTree  FileView  SearchView  GraphView  Tag Filters    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────────┐
│                   Backend (Python FastAPI)                 │
│  TreeService  FileService  WikiLinkParser  SearchService   │
│  GraphService SyncService                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
┌─────────────▼────────────┐  ┌────────▼──────────────────────┐
│ arc-reactor-doc/wiki/    │  │ SQLite                        │
│ Markdown files           │  │ metadata + links + FTS index  │
└──────────────────────────┘  └───────────────────────────────┘
```

### 4.1 职责划分

- 文件系统：
  - 保存原始 Markdown 文件。
  - 提供目录结构、正文、front-matter、heading 等原始信息。
- 后端：
  - 读取文件系统。
  - 解析 front-matter、heading、WikiLink。
  - 管理 SQLite 索引。
  - 暴露只读 API 和手动同步 API。
- 前端：
  - 展示目录树、文档内容、搜索结果、反向链接、图谱。
  - 负责路由跳转和交互，不直接访问文件系统。

---

## 5. WikiLink 规则

### 5.1 首版支持的语法

```text
[[target]]
[[target#heading]]
[[#heading]]
[[target|display]]
[[target#heading|display]]
```

### 5.2 解析结果字段

每个 WikiLink 在后端解析后都应至少产出以下字段：

- `raw_text`: 原始文本，例如 `[[foo#bar|baz]]`
- `target_raw`: 原始 target，例如 `foo`
- `target_path`: 解析后的目标相对路径，若无法唯一解析则为 `NULL`
- `target_anchor`: 目标 heading anchor，若无则为 `NULL`
- `display_text`: 显示文本，若无则为 `NULL`
- `source_line`: 所在行号
- `source_column`: 所在列号
- `is_resolved`: 是否成功唯一解析
- `resolution_error`: `not_found` / `ambiguous` / `invalid`

### 5.3 路径解析规则

按以下顺序解析 `target`：

1. 如果 `target` 包含 `/`，按相对路径解析。
2. 如果 `target` 不包含 `/`，按文件 `stem` 匹配。
3. 如果匹配到 1 个文件，则解析成功。
4. 如果匹配到 0 个文件，则记为 `not_found`。
5. 如果匹配到多个文件，则记为 `ambiguous`，不自动猜测。

说明：

- `target` 可以省略 `.md`，解析时自动补全。
- `[[#heading]]` 表示当前文件内锚点跳转，此时 `target_path` 等于当前文件路径。
- `heading` 的 anchor 生成算法必须由前后端共享同一规则，避免跳转不一致。

### 5.4 Heading 规范

- 后端在同步时提取所有 Markdown heading。
- 每个 heading 生成稳定的 `anchor_slug`。
- 若同文件内存在同名 heading，按常见 Markdown 规则追加后缀去重，例如：
  - `overview`
  - `overview-1`
  - `overview-2`

---

## 6. 数据库设计

### 6.1 设计原则

- 数据表以“可重建”为前提，优先简单稳定。
- 首版不做 `backlinks` 冗余缓存表，反向链接通过 `links` 表直接查询生成。
- 首版不做 external-content FTS，避免 `files` 表与 FTS 表结构强耦合。

### 6.2 表结构

```sql
CREATE TABLE files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    path          TEXT    NOT NULL UNIQUE,   -- 相对于 wiki/ 的路径，含 .md
    parent_path   TEXT    NOT NULL,          -- 父目录，相对路径；根目录记为 ''
    stem          TEXT    NOT NULL,          -- 文件名，不含 .md
    title         TEXT,                      -- front-matter.title，若无则回退到 stem
    category      TEXT,                      -- sources | entities | root | custom
    tags_json     TEXT    NOT NULL DEFAULT '[]',
    mtime_ns      INTEGER NOT NULL,
    size_bytes    INTEGER NOT NULL,
    content_hash  TEXT    NOT NULL,          -- 用于判断是否需要重建索引
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE INDEX idx_files_parent_path ON files(parent_path);
CREATE INDEX idx_files_stem ON files(stem);
CREATE INDEX idx_files_category ON files(category);

CREATE TABLE file_tags (
    file_id       INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    tag           TEXT    NOT NULL,
    normalized    TEXT    NOT NULL,
    PRIMARY KEY (file_id, normalized)
);

CREATE INDEX idx_file_tags_normalized ON file_tags(normalized);

CREATE TABLE headings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id       INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    level         INTEGER NOT NULL,
    text          TEXT    NOT NULL,
    anchor_slug   TEXT    NOT NULL,
    line_no       INTEGER NOT NULL,
    UNIQUE (file_id, anchor_slug)
);

CREATE INDEX idx_headings_file_id ON headings(file_id);

CREATE TABLE links (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id   INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    raw_text         TEXT    NOT NULL,
    target_raw       TEXT    NOT NULL,
    target_path      TEXT,                    -- 解析成功后写入目标 path
    target_anchor    TEXT,                    -- heading anchor
    display_text     TEXT,                    -- 显示文本
    link_kind        TEXT    NOT NULL,        -- wiki | heading
    is_resolved      INTEGER NOT NULL,        -- 0 | 1
    resolution_error TEXT,                    -- NULL | not_found | ambiguous | invalid
    source_line      INTEGER NOT NULL,
    source_column    INTEGER NOT NULL
);

CREATE INDEX idx_links_source_file_id ON links(source_file_id);
CREATE INDEX idx_links_target_path ON links(target_path);

CREATE VIRTUAL TABLE file_search USING fts5(
    path UNINDEXED,
    title,
    body,
    tags,
    tokenize = 'unicode61'
);
```

### 6.3 说明

- `files.path` 是所有业务逻辑的唯一文件标识。
- `file_tags` 为标签的规范化拆表，避免后续做图谱和筛选时反复解析 JSON。
- `headings` 用于支持 `[[#heading]]`、`[[target#heading]]` 和页内目录能力。
- `links.target_path` 不使用外键，允许保留未解析或歧义链接，便于排错和 UI 提示。
- `file_search` 是纯索引表，不是内容主存储；其内容在同步时重建。

### 6.4 FTS 写入策略

- 每个文件在 `file_search` 中对应一条记录。
- 建议使用 `rowid = files.id`，保持索引记录与文件记录一一对应。
- 同步更新时：
  - 文件新增：插入 `file_search`
  - 文件更新：删除旧 `rowid` 后重插
  - 文件删除：删除对应 `rowid`

---

## 7. 同步策略

### 7.1 同步模式

- 启动时执行一次 `full` 同步，确保 SQLite 与当前文件系统一致。
- 运行过程中仅提供手动同步接口：
  - `incremental`: 扫描文件变化，更新受影响文件及其派生数据
  - `full`: 清空索引并全量重建

首版不做文件系统 watcher，避免跨平台复杂度。

### 7.2 incremental 同步流程

```text
1. 扫描 wiki/ 下所有 .md 文件
2. 计算每个文件的 path、mtime_ns、size_bytes、content_hash
3. 找出新增、修改、删除的文件
4. 对新增和修改文件：
   - 解析 front-matter
   - 提取 heading
   - 提取 WikiLink
   - 更新 files / file_tags / headings / links
   - 更新 file_search
5. 对已删除文件：
   - 删除 files 记录
   - 依赖 ON DELETE CASCADE 清理 tags / headings / links
   - 删除 file_search 中对应记录
6. 重新解析所有“引用了已删除或曾歧义目标”的文件，保证解析结果收敛
```

### 7.3 full 同步流程

```text
1. 清空 files / file_tags / headings / links / file_search
2. 扫描全部 Markdown 文件
3. 逐个重建元数据、heading、links、FTS
4. 返回统计信息
```

### 7.4 同步返回结果

```json
{
  "mode": "incremental",
  "scanned": 128,
  "created": 3,
  "updated": 7,
  "deleted": 1,
  "reparsed": 4,
  "warnings": [
    {
      "path": "entities/overview.md",
      "message": "wikilink target 'foo' is ambiguous"
    }
  ],
  "took_ms": 184
}
```

---

## 8. API 设计

### 8.1 通用约定

- 所有 API 前缀统一为 `/api`。
- 所有文件路径参数统一使用 `{file_path:path}`。
- 前端传参时使用 URL 编码后的相对路径，例如：
  - `entities/karpathy.md`
  - `sources/topic/a.md`

### 8.2 文件与目录 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/tree` | 获取目录树 |
| `GET` | `/api/files/{file_path:path}` | 获取单个文件详情 |
| `GET` | `/api/files/{file_path:path}/raw` | 获取原始 Markdown |
| `GET` | `/api/files/{file_path:path}/links` | 获取出站链接 |
| `GET` | `/api/files/{file_path:path}/backlinks` | 获取反向链接 |

`GET /api/files/{file_path:path}` 返回示例：

```json
{
  "path": "entities/karpathy.md",
  "title": "Karpathy 个人知识库构建方法",
  "stem": "karpathy",
  "category": "entities",
  "tags": ["LLM", "PKM"],
  "headings": [
    {"level": 2, "text": "背景", "anchor": "背景"}
  ],
  "content": "# Karpathy\n\n...",
  "mtime_ns": 1712735000000000000
}
```

### 8.3 搜索 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/search?q={keyword}` | 全文搜索 |
| `GET` | `/api/search?q={keyword}&category=entities` | 按分类过滤 |
| `GET` | `/api/tags` | 获取标签聚合 |

搜索返回示例：

```json
{
  "results": [
    {
      "path": "entities/karpathy.md",
      "title": "Karpathy 个人知识库构建方法",
      "snippet": "...<mark>知识库</mark>构建方法...",
      "score": -4.23,
      "tags": ["LLM", "PKM"]
    }
  ],
  "total": 1,
  "took_ms": 4
}
```

说明：

- FTS5 的 `bm25()` 分值越小通常相关性越高，因此 `score` 不要求归一化到 0 到 1。

### 8.4 图谱 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/graph` | 获取图谱数据 |

支持查询参数：

- `category`: `all` / `sources` / `entities`
- `include_tags`: `true` / `false`

图谱返回示例：

```json
{
  "nodes": [
    {"id": "entities/karpathy.md", "type": "file", "label": "Karpathy 个人知识库构建方法"},
    {"id": "tag:llm", "type": "tag", "label": "LLM"}
  ],
  "edges": [
    {"source": "entities/karpathy.md", "target": "sources/karpathy-video.md", "type": "wikilink"},
    {"source": "entities/karpathy.md", "target": "tag:llm", "type": "tag"}
  ]
}
```

### 8.5 同步与健康检查 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/sync` | 触发索引同步 |
| `GET` | `/api/health` | 健康检查 |

`POST /api/sync` 请求体示例：

```json
{
  "mode": "incremental"
}
```

---

## 9. 前端设计

### 9.1 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 与现有方案保持一致 |
| 路由 | Vue Router | 支持 catch-all 文件路径路由 |
| 状态管理 | Pinia | 管理当前文档、目录树、搜索状态 |
| UI | Naive UI | 提供基础组件 |
| Markdown 渲染 | markdown-it | 便于扩展 WikiLink 和 heading anchor |
| 代码高亮 | highlight.js | 用于代码块渲染 |
| 图谱 | D3.js | 基础力导向图即可 |

### 9.2 页面与路由

| 页面 | 路由 | 说明 |
|------|------|------|
| 首页 | `/` | 文件树、最近同步状态、搜索入口 |
| 阅读页 | `/file/:filePath(.*)*` | Markdown 阅读、出链、反链 |
| 搜索页 | `/search` | 搜索结果列表 |
| 图谱页 | `/graph` | 全局图谱视图 |

### 9.3 核心组件

| 组件 | 说明 |
|------|------|
| `FileTree.vue` | 目录树，支持多级目录展开 |
| `MarkdownRenderer.vue` | Markdown 渲染和 WikiLink 点击跳转 |
| `BacklinksPanel.vue` | 展示当前文件被哪些文件引用 |
| `SearchBar.vue` | 搜索输入和参数切换 |
| `SearchResults.vue` | 搜索结果与 snippet 展示 |
| `GraphView.vue` | 文件图谱渲染 |
| `TagFilter.vue` | 标签筛选 |
| `SyncStatus.vue` | 展示最近同步时间和结果 |

### 9.4 前端实现约束

- 文件阅读页以 `path` 为唯一标识，不用 `title` 或 `stem` 做路由参数。
- 渲染 Markdown 时，WikiLink 点击后必须跳到解析后的 `target_path`。
- 如果后端返回某个链接 `is_resolved = false`，前端只做样式标识，不做盲跳。
- 图谱页首版只要求支持：
  - 节点拖拽
  - 缩放
  - 点击文件节点跳转阅读页

---

## 10. 后端项目结构

```text
wiki-knowledge-base/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── schemas/
│   │   │   ├── file.py
│   │   │   ├── search.py
│   │   │   ├── graph.py
│   │   │   └── sync.py
│   │   ├── routers/
│   │   │   ├── tree.py
│   │   │   ├── files.py
│   │   │   ├── search.py
│   │   │   ├── graph.py
│   │   │   ├── sync.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── file_service.py
│   │   │   ├── tree_service.py
│   │   │   ├── search_service.py
│   │   │   ├── graph_service.py
│   │   │   └── sync_service.py
│   │   ├── indexing/
│   │   │   ├── frontmatter.py
│   │   │   ├── headings.py
│   │   │   ├── wikilink.py
│   │   │   └── fts.py
│   │   └── sql/
│   │       └── schema.sql
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── views/
│   │   ├── components/
│   │   └── utils/
│   └── package.json
└── docs/
    └── WIKI_KNOWLEDGE_BASE_DEV_PLAN.md
```

---

## 11. 实施计划

### Phase 1：后端骨架与核心契约

- [ ] 初始化 FastAPI 项目和配置项
- [ ] 固化 `WIKI_ROOT` 与路径规范化逻辑
- [ ] 建立 SQLite schema
- [ ] 实现 `GET /api/health`
- [ ] 实现 `GET /api/tree`

验收标准：

- 服务可启动
- 能正确列出 `wiki/` 目录树
- 对非法路径请求返回 4xx

### Phase 2：文件读取与 Markdown 元信息

- [ ] 实现 `GET /api/files/{file_path:path}`
- [ ] 实现 `GET /api/files/{file_path:path}/raw`
- [ ] 实现 front-matter 提取
- [ ] 实现 heading 提取与 anchor 生成

验收标准：

- 能正确读取任意合法 Markdown 文件
- 能返回标题、标签、heading 列表
- 子目录文件路径可正常访问

### Phase 3：同步与索引

- [ ] 实现 `POST /api/sync`
- [ ] 实现 `full` 与 `incremental` 两种模式
- [ ] 实现 `files`、`file_tags`、`headings`、`links`、`file_search` 的维护逻辑
- [ ] 处理文件删除和重命名后的索引清理

验收标准：

- 新增文件后可被检索
- 删除文件后搜索和反链不再残留
- 重名 `stem` 文件出现时，歧义链接会被标记为 `ambiguous`

### Phase 4：WikiLink、反向链接与搜索

- [ ] 实现 WikiLink 解析器
- [ ] 实现 `GET /api/files/{file_path:path}/links`
- [ ] 实现 `GET /api/files/{file_path:path}/backlinks`
- [ ] 实现 `GET /api/search`
- [ ] 实现 `GET /api/tags`

验收标准：

- 支持 `[[target]]`
- 支持 `[[target#heading]]`
- 支持 `[[#heading]]`
- 支持 `[[target|display]]`
- 搜索可返回标题、snippet、标签

### Phase 5：前端阅读体验

- [ ] 初始化 Vue 3 + Vite + Naive UI
- [ ] 接入目录树和阅读页
- [ ] 实现 MarkdownRenderer 和 WikiLink 跳转
- [ ] 实现 BacklinksPanel

验收标准：

- 可以从目录树打开文档
- 点击已解析的 WikiLink 可以正确跳转
- 阅读页可以展示反向链接

### Phase 6：图谱与收尾

- [ ] 实现 `GET /api/graph`
- [ ] 实现 GraphView
- [ ] 增加同步状态展示
- [ ] 增加启动说明和部署文档

验收标准：

- 图谱能展示文件节点与链接边
- 开启 `include_tags=true` 时能展示标签节点
- 用户可从图谱点击进入文件阅读页

---

## 12. 关键测试用例

### 12.1 路径与安全

- [ ] `index.md` 可正常访问
- [ ] `entities/topic/a.md` 可正常访问
- [ ] `../secret.md` 被拒绝
- [ ] 绝对路径被拒绝

### 12.2 WikiLink

- [ ] `[[foo]]` 命中唯一文件
- [ ] `[[foo]]` 命中多个文件时返回 `ambiguous`
- [ ] `[[foo#bar]]` 能定位到目标 heading
- [ ] `[[#bar]]` 能定位到当前文件 heading
- [ ] `[[foo|显示名]]` 正确保留 display text

### 12.3 索引一致性

- [ ] 新增文件后可搜索
- [ ] 修改标题后搜索结果更新
- [ ] 删除文件后反链消失
- [ ] 同步两次结果一致且无重复数据

### 12.4 图谱

- [ ] 文件节点数量与索引文件数量一致
- [ ] 关系边数量与已解析链接数量一致
- [ ] 标签节点去重正确

---

## 13. 启动方式

### 13.1 后端

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 13.2 前端

```powershell
cd frontend
npm install
npm run dev
```

### 13.3 配置项

建议最少提供以下环境变量：

```text
WIKI_ROOT=../arc-reactor-doc/wiki
SQLITE_PATH=./data/wiki_index.db
APP_PORT=8000
```

---

## 14. 已知限制与后续扩展

### 当前限制

- 只读，不支持在线编辑
- 同步依赖手动触发，不监听文件系统变化
- SQLite 适合单机本地使用，不适合多人并发写入
- 图谱首版只关注文件级与标签级关系，不做复杂聚类分析

### 后续扩展方向

- 文件 watcher 自动增量同步
- Git 集成与变更历史展示
- Obsidian 兼容增强
- LLM 问答和知识摘要
- 多用户权限与远程部署

---

## 15. 实施结论

这版方案的关键收敛点如下：

- 唯一数据源固定为 `arc-reactor-doc/wiki/`
- 文件唯一标识固定为相对路径 `path`
- WikiLink 允许按 `stem` 解析，但遇到歧义不猜测
- FTS 使用独立 `file_search` 表，不再与 `files` 表做冲突设计
- 反向链接由 `links` 实时查询生成，不引入首版缓存表
- API 和前端路由统一支持多级目录路径
- 同步明确区分 `incremental` 与 `full`

按本文档实施，前后端可以并行推进，且首版能稳定落地。
