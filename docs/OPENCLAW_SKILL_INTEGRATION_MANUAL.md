# openclaw Skill 标准接入操作手册

## 1. 文档目的

本文档面向 `openclaw` Skill 的开发者或维护者，说明如何将 Skill 稳定接入当前 `Report Center + LLM Wiki` 系统。

目标不是让 Skill 直接维护整套知识库，而是让 Skill 稳定完成：

1. 原始内容落地
2. 标准化报告输出
3. 触发系统同步
4. 可选触发知识编译

## 2. 接入原则

### 2.1 Skill 负责什么

Skill 负责：

- 抓取来源内容
- 生成总结报告
- 计算报告基础元数据
- 把报告写入标准目录
- 可选调用 `/api/sync`
- 可选调用 `/api/wiki/compile`

### 2.2 Skill 不负责什么

Skill 不负责：

- 直接写入 SQLite
- 直接维护 `wiki_pages`
- 直接维护 `knowledge_tasks`
- 直接修改治理状态

这些都应交给后端完成。

## 3. 推荐接入等级

### 3.1 Level 1

Skill 只负责写报告文件。

后续由人工在系统中执行：

- `Sync`
- `Compile`

适用场景：

- 先求稳定
- 新 Skill 刚接入
- 想快速打通最小闭环

### 3.2 Level 2

Skill 写完报告后，自动调用：

- `POST /api/sync`

然后由人工决定是否执行：

- `POST /api/wiki/compile`

这是当前最推荐的接入级别。

### 3.3 Level 3

Skill 写完报告后，自动调用：

- `POST /api/sync`
- `POST /api/wiki/compile`

适用场景：

- 报告质量很稳定
- 主题范围清晰
- 已接受一定程度的自动沉淀

## 4. 标准目录约定

Skill 应遵循以下目录约定：

- 原始内容：`raw/`
- 标准报告：`reports/YYYY/MM/`

推荐路径示例：

```text
raw/2026/04/src_20260413_xxx.html
raw/2026/04/src_20260413_xxx.json
reports/2026/04/rpt_20260413_101523_a1b2c3d4.md
```

## 5. 报告文件标准

### 5.1 编码要求

- 使用 UTF-8
- 行结尾统一即可，推荐 LF

### 5.2 文件命名规则

推荐：

```text
rpt_YYYYMMDD_HHMMSS_<source_hash>.md
```

示例：

```text
rpt_20260413_101523_a1b2c3d4.md
```

## 6. front matter 标准

Skill 生成的报告必须带 YAML front matter。

### 6.1 必填字段

- `report_id`
- `title`
- `source_ref`
- `skill_name`
- `generated_at`
- `status`
- `summary`

### 6.2 推荐字段

- `source_url`
- `source_domain`
- `source_type`
- `author`
- `language`
- `tags`
- `related_urls`

### 6.3 标准模板

```md
---
report_id: rpt_20260413_101523_a1b2c3d4
title: OpenClaw Skill 标准接入示例报告
source_ref: https://example.com/article
source_url: https://example.com/article
source_domain: example.com
source_type: url
skill_name: openclaw-link-summary
generated_at: 2026-04-13T10:15:23+08:00
author: openclaw
tags:
  - openclaw
  - integration
status: published
language: zh-CN
summary: 这是一篇用于验证 openclaw Skill 接入链路的示例报告。
related_urls:
  - https://example.com/article
  - https://example.com/reference
---

# OpenClaw Skill 标准接入示例报告

正文内容...
```

## 7. 字段约束说明

### 7.1 `report_id`

要求：

- 全局唯一
- 一旦生成后不再变更

推荐生成方式：

```text
rpt_<timestamp>_<source_hash>
```

### 7.2 `source_ref`

这是当前系统中的主来源字段。

要求：

- 必须填写
- URL 来源时通常等于 `source_url`
- 非 URL 来源时，也可以是本地路径、文件引用或其他来源标识

注意：

- `source_ref` 是主字段
- `source_url` 只是兼容字段

### 7.3 `source_domain`

URL 来源时：

- 建议填主域名，如 `example.com`

非 URL 来源时：

- 可填 `local`
- 或填更具体的来源类别

### 7.4 `generated_at`

要求：

- 使用 ISO 8601 格式

示例：

```text
2026-04-13T10:15:23+08:00
```

### 7.5 `status`

当前推荐值：

- `published`
- `draft`
- `archived`
- `failed`

大多数正常报告使用：

```text
published
```

### 7.6 `summary`

要求：

- 这是列表页和查询页直接使用的短摘要
- 长度适中，建议 1 到 3 句话

### 7.7 `tags`

要求：

- 始终输出数组
- 即使只有一个值也保持数组结构

推荐：

- 至少包含主题标签
- 可补充来源类别或场景标签

## 8. `content_hash` 处理建议

当前系统在同步时会重新计算正文 hash，因此 Skill 不强制必须写入 `content_hash`。

但如果你希望让 Skill 端和系统端更容易对账，建议 Skill 也按同样规则计算：

- 计算对象：去掉 front matter 后的正文
- 算法：SHA-256
- 存储格式：`sha256:<hex>`

## 9. Skill 输出标准流程

推荐标准流程如下：

```text
用户输入链接/主题
  -> Skill 抓取原始内容
  -> Skill 将原始内容落入 raw/
  -> Skill 生成总结报告
  -> Skill 组装 front matter
  -> Skill 写入 reports/YYYY/MM/*.md
  -> Skill 调用 /api/sync
  -> 可选调用 /api/wiki/compile
```

## 10. 标准接入步骤

### 10.1 第一步：写入原始内容

建议把抓取到的源内容保存在 `raw/`，便于追溯。

例如：

```text
raw/2026/04/src_20260413_article.html
raw/2026/04/src_20260413_article.json
```

### 10.2 第二步：写入标准报告

把生成后的 Markdown 报告写入：

```text
reports/YYYY/MM/
```

### 10.3 第三步：触发同步

调用：

```http
POST /api/sync
Content-Type: application/json
```

请求体：

```json
{
  "mode": "incremental"
}
```

### 10.4 第四步：可选触发知识编译

调用：

```http
POST /api/wiki/compile
Content-Type: application/json
```

请求体示例：

```json
{
  "report_id": "rpt_20260413_101523_a1b2c3d4",
  "mode": "propose"
}
```

推荐默认：

- 新接入 Skill：`propose`
- 稳定 Skill：按场景逐步引入 `apply_safe`

## 11. API 调用示例

### 11.1 PowerShell 调用 `sync`

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/sync" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"mode":"incremental"}'
```

### 11.2 PowerShell 调用 `compile`

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/wiki/compile" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"report_id":"rpt_20260413_101523_a1b2c3d4","mode":"propose"}'
```

### 11.3 Python 调用示例

```python
import requests

requests.post(
    "http://127.0.0.1:8000/api/sync",
    json={"mode": "incremental"},
    timeout=30,
)

requests.post(
    "http://127.0.0.1:8000/api/wiki/compile",
    json={
        "report_id": "rpt_20260413_101523_a1b2c3d4",
        "mode": "propose",
    },
    timeout=30,
)
```

## 12. 推荐接入实现

### 12.1 推荐做法

当前推荐：

1. Skill 先稳定写报告
2. 写完后自动调用 `sync`
3. `compile` 先保留给人工触发

这是最稳的 Level 2 接入方式。

### 12.2 不推荐做法

不建议：

- Skill 直接写 SQLite
- Skill 自己维护 Wiki 文件
- Skill 直接修改冲突和任务表
- Skill 在报告质量不稳定时默认 `apply_safe`

## 13. 异常处理规范

当 Skill 执行失败时，建议区分以下几类失败：

### 13.1 抓取失败

建议：

- 记录错误日志
- 不生成正式报告

### 13.2 总结失败

建议：

- 记录错误日志
- 不生成正式报告

### 13.3 写文件失败

建议：

- 记录错误日志
- 不触发 `sync`

### 13.4 API 调用失败

如果报告已经写入成功，但 `sync` 或 `compile` 调用失败：

- 不要删除报告文件
- 记录失败日志
- 允许后续人工在 `/app/#/admin` 手动执行

## 14. 最小验收清单

一个 Skill 完成接入，至少应满足：

1. 能把报告稳定写进 `reports/YYYY/MM/`
2. front matter 符合标准
3. 执行 `POST /api/sync` 后，`Reports` 页面能看到新报告
4. 执行 `POST /api/wiki/compile` 后，`Wiki` 或 `Tasks` 页面能看到结果
5. 生成的报告可以在 `Ask` 中作为证据被检索到

## 15. 推荐联调流程

每次新 Skill 接入时，按下面顺序联调：

1. 先人工生成 1 篇测试报告
2. 检查 front matter 是否合规
3. 手动执行 `sync`
4. 查看 `Reports`
5. 手动执行 `compile`
6. 查看 `Wiki` 和 `Tasks`
7. 到 `Ask` 提 1 个围绕该报告的问题
8. 验证系统是否能命中该报告

## 16. 接入结论

对当前系统，最合适的 Skill 接入标准是：

- 文件落地为主
- API 驱动同步
- 知识编译由后端负责
- 治理与回写仍留在系统中完成

这能保证：

- Skill 足够轻
- 后端职责清晰
- 系统可追踪、可治理、可扩展
