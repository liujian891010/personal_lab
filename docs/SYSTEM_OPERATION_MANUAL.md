# Report Center + LLM Wiki 操作说明书

## 1. 文档目的

本文档面向系统使用者，说明如何启动、进入、使用和维护当前的 `Report Center + LLM Wiki` 系统。

系统目标不是“只存报告”，而是把 `报告 -> Wiki -> 问答 -> 治理` 串成一个闭环。

## 2. 系统入口

### 2.1 启动方式

在项目根目录执行：

```powershell
python -m uvicorn backend.app.main:app --reload
```

### 2.2 访问地址

- 工作台：`http://127.0.0.1:8000/app/`
- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/health`

### 2.3 前提目录

系统默认使用以下目录：

- `raw/`
- `reports/`
- `knowledge/`
- `data/`
- `logs/`

## 3. 页面说明

### 3.1 Reports

入口：`/app/#/reports`

用途：

- 查看报告列表
- 根据关键词、标签、域名、状态、Skill 名称进行筛选
- 进入报告详情页查看正文和链接

适用场景：

- 确认 `openclaw` Skill 的报告是否已经被系统识别
- 检查报告摘要和元数据是否正确
- 快速定位某篇报告

### 3.2 Report Detail

入口：`/app/#/reports/{report_id}`

用途：

- 查看报告完整 Markdown 内容
- 查看来源引用
- 查看解析出的外链
- 查看报告标签、状态、更新时间

适用场景：

- 人工审核报告内容
- 排查 front matter 是否填写规范
- 验证来源链接是否正确

### 3.3 Wiki

入口：`/app/#/wiki`

用途：

- 查看知识页列表
- 按关键词、标签、页面类型、状态筛选
- 进入知识页详情

当前页面类型包括：

- `entity`
- `concept`
- `topic`
- `question`
- `timeline`

### 3.4 Wiki Detail

入口：`/app/#/wiki/{slug}`

用途：

- 查看知识页正文
- 查看来源报告
- 查看关联知识页
- 查看页面状态、slug、page_id、更新时间

适用场景：

- 审核 compile 是否已经形成可用知识
- 判断某个主题是否已经沉淀
- 追踪页面依赖关系

### 3.5 Ask

入口：`/app/#/ask`

用途：

- 对当前知识库提问
- 查看问答结果
- 查看证据来源
- 决定是否回写

系统查询顺序：

1. 先查 Wiki
2. 再补充 Report

Ask 页面支持两种回写：

- `Question Page`
- `Review Task`

适用场景：

- 复用历史报告和知识页回答问题
- 将高价值问题沉淀成长期 FAQ

### 3.6 Tasks

入口：`/app/#/tasks`

用途：

- 查看治理任务
- 按状态、任务类型、目标类型筛选

常见任务类型：

- `compile_page`
- `fill_gap`
- `review_answer_writeback`
- `resolve_conflict`
- `update_page`

适用场景：

- 查看哪些知识还未落地
- 查看哪些问答需要人工审核
- 查看哪些冲突需要处理

### 3.7 Conflicts

入口：`/app/#/conflicts`

用途：

- 查看冲突记录
- 按状态和严重级别筛选

常见冲突来源：

- 页面类型冲突
- 未解析的 Wiki 链接
- 新旧知识主张不一致

### 3.8 Admin

入口：`/app/#/admin`

用途：

- 手动执行 `sync`
- 手动执行 `compile`
- 手动执行 `lint`
- 查看最近操作结果
- 查看当前系统健康状态

## 4. 核心操作流程

### 4.1 新报告进入系统

当 `openclaw` Skill 生成一篇新报告后，推荐按以下步骤操作：

1. 打开 `Admin`
2. 执行 `Run Sync`
3. 打开 `Reports`，确认新报告已经出现

如果 `Reports` 中没有看到新报告，优先检查：

- 报告文件是否写入 `reports/YYYY/MM/`
- front matter 是否缺字段
- `logs/` 中是否有异常

### 4.2 报告沉淀为 Wiki

当报告已经入库后：

1. 在 `Admin` 执行 `Run Compile`
2. 推荐先用 `mode=propose`
3. 如果是低风险场景，可用 `mode=apply_safe`
4. 打开 `Wiki` 查看是否出现新知识页
5. 打开 `Tasks` 查看是否生成编译待办

什么时候用 `propose`：

- 希望先人工审核
- 新主题较多
- 内容质量不稳定

什么时候用 `apply_safe`：

- 已知报告结构稳定
- 允许低风险自动落页
- 先追求沉淀速度

### 4.3 用 Ask 做问答和回写

推荐操作：

1. 进入 `Ask`
2. 输入问题
3. 查看答案和证据
4. 判断这是不是高频问题
5. 如值得长期保留，点击 `回写 Question Page`
6. 如暂不适合直接回写，点击 `生成 Review Task`

适合直接回写为 Question Page 的情况：

- 这是一个会反复被问到的问题
- 当前答案引用证据比较充分
- 问题表达本身就适合长期复用

适合先生成 Review Task 的情况：

- 证据还不够稳定
- 需要人工修改答案
- 不希望直接污染知识库

### 4.4 用 Lint 做治理

当系统中报告和知识页逐渐增多后，建议定期在 `Admin` 执行 `Run Lint`。

`light` 模式适合：

- 日常快速检查
- 只关心显著问题

`full` 模式适合：

- 阶段性治理
- 准备发版
- 准备大规模导入新报告前后

Lint 当前会重点发现：

- 未解析 Wiki 链接
- 可回写但未沉淀的问答
- 已入库但还没有知识页承接的报告

## 5. 推荐日常 SOP

### 5.1 日常更新

1. 让 Skill 生成报告
2. 执行 `Sync`
3. 检查 `Reports`
4. 执行 `Compile`
5. 检查 `Wiki`
6. 必要时执行 `Lint`

### 5.2 日常查询

1. 在 `Ask` 提问题
2. 先看有没有 Wiki 命中
3. 再看补充报告证据
4. 决定是否回写

### 5.3 周期治理

建议每周至少做一次：

1. 执行 `Run Lint`
2. 打开 `Tasks`
3. 优先处理：
   `resolve_conflict`
   `fill_gap`
   `review_answer_writeback`
4. 打开 `Conflicts`
5. 清理明显错误的知识关系

## 6. 常见操作建议

### 6.1 我想确认一篇报告有没有入库

做法：

1. 在 `Reports` 里搜标题
2. 如果没有，去 `Admin` 执行 `Sync`
3. 如果还没有，检查该报告 front matter 是否合规

### 6.2 我想把一篇报告变成知识页

做法：

1. 确认报告已经在 `Reports`
2. 在 `Admin` 执行 `Compile`
3. 去 `Wiki` 搜标题或主题词
4. 如没有生成，去 `Tasks` 看是否有 `compile_page`

### 6.3 我想让一个问题以后能直接复用

做法：

1. 在 `Ask` 输入问题
2. 确认答案可接受
3. 点击 `回写 Question Page`
4. 去 `Wiki` 搜这个问题对应的 question 页面

### 6.4 我发现知识页不准

做法：

1. 去 `Wiki Detail` 查看来源报告
2. 去 `Reports` 查看对应报告正文
3. 判断是报告源问题、编译问题，还是链接关系问题
4. 必要时用 `Lint` 生成治理待办

## 7. 故障排查

### 7.1 页面打不开

检查：

- 后端是否启动
- `http://127.0.0.1:8000/api/health` 是否返回 `200`
- 是否访问的是 `/app/`

### 7.2 报告看不到

检查：

- 文件是否真的在 `reports/` 下
- 是否执行过 `Sync`
- 报告 front matter 是否缺少必填字段

### 7.3 Wiki 没生成

检查：

- 是否执行过 `Compile`
- `Compile` 用的是 `propose` 还是 `apply_safe`
- `Tasks` 是否有 `compile_page`

### 7.4 Ask 没有结果

检查：

- 是否已有相关 Wiki 或 Report
- 问题关键词是否过于宽泛
- 先去 `Reports` 或 `Wiki` 验证基础数据是否存在

### 7.5 Conflicts 很多

通常说明：

- Wiki 链接引用不规范
- 自动编译命中了模糊主题
- 某些页面 slug 或主题命名需要统一

## 8. 当前版本边界

当前系统是 MVP 工作台，重点是可运行和可治理，不是最终形态。

当前已实现：

- 报告列表和详情
- Wiki 列表和详情
- 问答与回写
- 任务与冲突查看
- Sync / Compile / Lint 操作台

当前未实现或未闭环：

- 页面内直接编辑知识页
- 任务状态流转按钮
- 冲突在线裁决按钮
- 更强的 Markdown 渲染器
- 向量召回和高级 RAG

## 9. 推荐使用原则

- 报告先保证质量，再追求自动化
- Compile 默认先保守，再逐步放开
- 高价值问题要回写
- 定期做 Lint，不要把治理一直往后拖
- `Tasks` 和 `Conflicts` 要作为日常工作面板，而不是摆设
