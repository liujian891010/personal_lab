# Phase 4: 报告、Wiki、Query 读写链路改造

## 目标

把目前直接读写本地 `reports/raw/knowledge` 目录的逻辑，统一切到对象存储读写抽象层。

## 改造步骤

- 报告读取改造
  - `reports` 正文优先从对象存储读取
  - 搜索、详情、预览路径不再直接拼本地文件
- Wiki 编译产物改造
  - entity/topic/question/conflict 等知识文件统一使用对象存储 key
- Query / Sync / Compile 改造
  - 输入源改为对象存储对象
  - 需要本地文件的步骤只在 working 目录落临时副本
- 搜索与索引改造
  - SQLite / FTS 继续存索引
  - 正文检索命中后再按对象指针读取正文
- 下载与预览能力
  - 后端代理下载
  - 或生成对象存储临时签名 URL

## 重点检查

- 是否还有模块绕过 `StorageService` 直接访问磁盘
- 是否存在对象正文和索引内容不一致
- 是否会因为网络读取导致页面明显变慢
