# Phase 4: Wiki 存储层与知识索引

## 目标

在 Report 层之上建立 Wiki 知识层的文件结构、数据库结构和检索入口，为后续编译与问答打底。

## 前置条件

- Report API 已可用。
- 已确认 Wiki 页面模型和 `slug` 唯一约束。

## 任务清单

- 创建 `knowledge/` 子目录结构：
  - `entities/`
  - `concepts/`
  - `topics/`
  - `questions/`
  - `timelines/`
  - `conflicts/`
  - `digests/`
- 扩展 `schema.sql`，增加：
  - `wiki_pages`
  - `wiki_page_tags`
  - `wiki_links`
  - `page_sources`
  - `wiki_search_index`
- 实现 Wiki 页面 front matter 解析。
- 实现 `slug` 生成和唯一性校验。
- 实现 Wiki 页面索引器：
  - 扫描 `knowledge/**/*.md`
  - 维护 `wiki_pages`
  - 维护 `wiki_page_tags`
  - 维护 `wiki_links`
  - 维护 `page_sources`
  - 维护 `wiki_search_index`
- 实现 Wiki 页面基础接口：
  - `GET /api/wiki/pages`
  - `GET /api/wiki/pages/{page_id}`
  - `GET /api/wiki/by-slug/{slug}`

## 交付物

- Wiki 数据表与索引。
- Wiki 文件索引器。
- Wiki 页面读取接口。

## 验收标准

- 任意一个合法 Wiki 页面文件可以被索引入库。
- `slug` 冲突时会被拒绝或生成明确错误，不允许静默覆盖。
- `GET /api/wiki/by-slug/{slug}` 可稳定唯一命中。
- 页面详情接口可返回：
  - 页面元数据
  - 正文
  - 支撑报告
  - 相关知识页
- 删除知识页文件后，索引中的页面、标签、关系可正确清理。

## 风险与注意

- 这一阶段只做存取和索引，不做自动编译。
- `question` 页面仍是 `wiki_pages` 的一个 `page_type`，不要单独建另一套主存储。
