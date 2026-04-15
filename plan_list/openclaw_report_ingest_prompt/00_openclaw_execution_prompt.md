# OpenClaw 执行 Prompt

你现在要接入一个本地运行的知识库项目。

这个项目会被完整打包给同事，并且由同事在他自己的电脑上启动和运行。  
因此，你后续要访问的服务地址、要写入的文件路径、要触发的入库流程，全部都发生在“同事自己的电脑本地环境”中，而不是原开发机器。

请严格按照下面流程执行。

## 场景前提

1. 同事已经在自己的电脑上拿到完整项目代码。
2. 同事已经在自己的电脑上启动本地服务，例如：
   - 前端：`http://127.0.0.1:8002/app/`
   - 后端：`http://127.0.0.1:8002`
3. 你后续使用的 `project_root`，指的是“同事本机上的项目根目录”。
4. 你后续写入的 `data/workspaces/...`，指的是“同事本机项目目录里的本地文件”。
5. 你后续调用的 `/api/sync`、`/api/wiki/compile`，指的是“同事本机自己启动的服务”，不是其他人的电脑。

## 目标

把你生成的 Markdown 总结报告接入同事本机上的项目，使其能够：

- 进入报告中心
- 被 `/api/reports` 检索到
- 后续可选进入 `/api/wiki/compile`

## 必须遵守的规则

1. 不要调用 `/api/uploads`
2. 不要调用本地 `GET /api/auth/me` 获取 `userId`
3. 不要直接写数据库
4. 不要写全局 `reports/`
5. 不要直接写 `knowledge/`
6. 必须使用 `appkey` 调外部登录 API 获取 `userId`
7. 必须把报告写入 `data/workspaces/{userId}/reports/{yyyy}/{mm}/{report_id}.md`
8. 写完后必须调用本地 `POST /api/sync`
9. 如有需要，再调用 `POST /api/wiki/compile`

## 第一步：用 appkey 调外部登录 API

使用下面这个接口获取当前用户信息：

```http
GET https://sg-al-cwork-web.mediportal.com.cn/user/login/appkey?appKey=<APPKEY>&appCode=personal_lab
```

你必须从返回结果中提取：

- `userId`
- `userName`

返回示例：

```json
{
  "telephone": "15323771186",
  "userId": "0210023418672077",
  "userName": "刘健"
}
```

字段映射规则：

- `workspace_id = userId`
- `workspace_name = userName`

后续所有目录定位都必须以 `userId` 为准。

## 第二步：生成标准 Markdown 报告

你要生成一份 Markdown 文件，必须带 frontmatter。  
最少必须包含这些字段：

- `report_id`
- `title`
- `source_ref`
- `skill_name`
- `generated_at`
- `status`
- `summary`

推荐完整模板如下：

```md
---
report_id: rpt_20260415_110000_a1b2c3d4
title: OpenClaw 报告示例
source_ref: https://example.com/article/123
source_url: https://example.com/article/123
source_domain: example.com
source_type: url
skill_name: openclaw
generated_at: 2026-04-15T11:00:00+08:00
status: published
language: zh-CN
summary: 这是 openclaw 生成的一份总结报告，用于进入报告中心并参与后续 wiki 编译。
tags:
  - openclaw
  - example
related_urls:
  - https://example.com/article/123
author: openclaw
---

# OpenClaw 报告示例

## 摘要

这里写正文摘要。

## 关键信息

这里写提炼后的核心内容。

## 原始来源

- 来源地址：https://example.com/article/123

## 详细整理

这里放完整整理后的正文内容。
```

## Frontmatter 格式限制

你必须遵守以下约束：

1. 只使用简单 `key: value`
2. 列表字段使用这种格式：

```yaml
tags:
  - openclaw
  - example
```

3. 不要写嵌套对象
4. 不要写复杂 YAML
5. 不要写多行块文本
6. `summary` 保持单行
7. `skill_name` 固定写 `openclaw`
8. `status` 固定写 `published`

## report_id 规则

使用唯一的 `report_id`，建议格式：

```text
rpt_{YYYYMMDD}_{HHMMSS}_{short_hash}
```

例如：

```text
rpt_20260415_110000_a1b2c3d4
```

## 第三步：把报告写入当前用户工作区

你必须把文件写到：

```text
<project_root>/data/workspaces/{userId}/reports/{yyyy}/{mm}/{report_id}.md
```

这里的 `<project_root>` 指的是“同事本机上的项目根目录”。

例如，如果同事把项目放在：

```text
D:/WorkSpace/personal_lab
```

那么你应该写到：

```text
D:/WorkSpace/personal_lab/data/workspaces/0210023418672077/reports/2026/04/rpt_20260415_110000_a1b2c3d4.md
```

要求：

- 目录不存在就创建
- 文件名必须等于 `report_id + ".md"`
- 只能写到当前 `userId` 对应的工作区目录
- 不要写到其他用户目录
- 不要写到原开发机器目录

## 第四步：调用同事本机上的 sync 入库

写完文件后，调用同事本机上的本地接口：

```http
POST http://127.0.0.1:8002/api/sync
Header:
  X-Appkey: <APPKEY>
  Content-Type: application/json
Body:
{
  "mode": "incremental"
}
```

示例：

```bash
curl -X POST \
  -H "X-Appkey: <APPKEY>" \
  -H "Content-Type: application/json" \
  -d "{\"mode\":\"incremental\"}" \
  http://127.0.0.1:8002/api/sync
```

注意：

- 这里的 `127.0.0.1:8002` 指的是“同事自己电脑上正在运行的服务”
- 不要把请求发到其他人的电脑
- 必须带同一个 `APPKEY`
- 虽然不需要调用 `/api/auth/me`
- 但本地 `/api/sync` 仍然依赖 `X-Appkey` 来绑定当前用户上下文

## 第五步：可选调用同事本机上的 wiki compile

如果希望报告继续进入 wiki 编译链路，则调用：

```http
POST http://127.0.0.1:8002/api/wiki/compile
Header:
  X-Appkey: <APPKEY>
  Content-Type: application/json
Body:
{
  "mode": "propose",
  "report_id": "<你的report_id>"
}
```

默认使用：

- `mode = propose`

## 成功标准

执行完成后，应满足：

1. 已成功通过外部登录 API 获取 `userId`
2. 已成功生成标准 Markdown 报告
3. 已将文件写入同事本机项目目录下的 `data/workspaces/{userId}/reports/{yyyy}/{mm}/{report_id}.md`
4. 已成功调用同事本机上的 `POST /api/sync`
5. 报告后续可在同事本机运行的报告中心中被扫描和检索
6. 如触发 compile，则后续可进入 wiki 流程

## 最小时序

```text
1. 使用 appkey 调外部登录 API
2. 提取 userId 和 userName
3. 生成标准 report.md
4. 写入同事本机项目目录下的 data/workspaces/{userId}/reports/{yyyy}/{mm}/{report_id}.md
5. 调同事本机的 POST /api/sync
6. 可选调同事本机的 POST /api/wiki/compile
```

## 一句话执行要求

先用 `appkey` 调外部登录 API 获取 `userId`，再把标准 Markdown 报告写到“同事本机项目目录”的 `data/workspaces/{userId}/reports/...`，最后带同一个 `X-Appkey` 调“同事本机服务”的 `/api/sync` 完成入库。

## 入库成功后的查看路径

报告入库成功后，可以通过下面两种前端路径查看：

1. 完整后台详情页

```text
http://127.0.0.1:8002/app/#/reports/{report_id}
```

这个页面会显示：

- 报告正文
- 标签
- 来源信息
- 报告元数据
- 后台操作入口

2. 仅详情页

```text
http://127.0.0.1:8002/app/#/report-only/{report_id}
```

这个页面是一个更干净的只读详情页：

- 不显示 topbar
- 不显示主导航
- 只展示报告正文和基础元信息
- 更适合直接阅读、演示或分享

例如：

```text
http://127.0.0.1:8002/app/#/report-only/rpt_20260415_110000_a1b2c3d4
```

## 入库成功后的最小验证

在完成 `/api/sync` 后，至少执行以下验证：

1. 确认报告能在列表页中出现：

```text
http://127.0.0.1:8002/app/#/reports
```

2. 确认报告能通过完整后台详情页打开：

```text
http://127.0.0.1:8002/app/#/reports/{report_id}
```

3. 确认报告能通过仅详情页打开：

```text
http://127.0.0.1:8002/app/#/report-only/{report_id}
```
