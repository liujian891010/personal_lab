# APPKEY 登录与用户隔离排期索引

本目录聚焦两件事：

- 基于 `APPKEY` 的登录与身份解析
- 基于 `workspace_id` 的用户数据隔离

已知固定约束：

- `APPKEY` 对应的个人信息由外部接口直接返回，不需要在本项目中额外实现“获取个人信息 API”。
- 外部接口固定为：`GET https://sg-al-cwork-web.mediportal.com.com/user/login/appkey`
- 参数传递方式为 query 传参。

## 执行顺序

1. `01_appkey_login_and_identity_contract.md`
2. `02_workspace_storage_and_schema.md`
3. `03_request_context_and_access_control.md`
4. `04_sync_search_wiki_query_isolation.md`
5. `05_frontend_login_and_session_flow.md`
6. `06_migration_backfill_and_cutover.md`
7. `07_ops_audit_and_runbook.md`

## 分阶段原则

- 先固化身份契约，再落工作区隔离。
- 先建立后端可信上下文，再接前端登录页。
- 先改数据归属、SQL 和路径边界，再改搜索与后台任务。
- 先保证隔离正确，再考虑更细粒度权限和管理视角。
- 迁移、切换、回滚方案必须与功能开发同步设计。

## 总体验收标准

- 用户可通过 `APPKEY` 登录并获取稳定身份上下文。
- 所有业务数据都以 `workspace_id` 为归属主维度。
- 报告、上传、Wiki、问答、治理任务等都在当前工作区内隔离。
- 后台任务和全文索引不会扫描或污染其他工作区。
- 历史全局数据可迁移、可核验、可回滚。
