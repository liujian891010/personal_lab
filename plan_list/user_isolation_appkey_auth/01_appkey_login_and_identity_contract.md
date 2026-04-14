# Phase 1: APPKEY 登录与身份契约
## 目标

建立 `APPKEY -> 固定外部登录接口 -> UserContext` 的统一身份链路，明确登录交换、会话管理和后端可信用户上下文，为后续工作区隔离提供稳定输入。

## 前置条件

- 已确认外部身份接口固定为：
  - `GET https://sg-al-cwork-web.mediportal.com.com/user/login/appkey`
- 已确认该接口通过 query 传参接收 `APPKEY`。
- 已确认该接口至少能返回稳定的 `user_id`。
- 已明确首版是否能直接返回 `workspace_id`，或采用 `workspace_id = user_id` 的兜底策略。

## 任务清单

- 明确登录接口契约：
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `POST /api/auth/logout`
- 设计登录请求体：
  - `appkey`
- 固化外部接口调用约束：
  - 请求方法：`GET`
  - 请求地址：`https://sg-al-cwork-web.mediportal.com.com/user/login/appkey`
  - 参数位置：query
- 设计登录成功返回内容：
  - `user_id`
  - `user_name`
  - `workspace_id`
  - `workspace_name`
  - `roles`
  - `expires_at`
- 固化后端内部 `UserContext` 结构。
- 明确后端登录时直接调用固定外部接口校验 `APPKEY` 并拉取用户信息。
- 不在本项目中额外实现“APPKEY 获取个人信息”的中间业务 API。
- 设计会话策略：
  - 推荐 HttpOnly Cookie Session
  - 备选 Bearer Token / JWT
- 明确失败场景与错误语义：
  - APPKEY 无效
  - 业务 API 超时
  - 用户状态禁用
  - 用户信息不完整
- 明确 `APPKEY` 使用边界：
  - 仅用于登录交换
  - 不直接进入后续业务接口
  - 不明文写入日志

## 交付物

- 登录时序图。
- `UserContext` 字段契约说明。
- 外部接口调用契约说明。
- 认证接口输入输出说明。
- 401/403 错误码使用规范。

## 验收标准

- 无效 `APPKEY` 无法登录。
- 登录成功后，后端可稳定解析 `current_user/current_workspace`。
- 会话过期后，接口会返回明确的未登录错误。
- 系统内部后续业务访问不再依赖前端重复传 `user_id` 或 `workspace_id`。
- 后端登录链路只依赖固定外部接口，不额外引入新的个人信息代理 API。

## 风险与注意事项

- 若固定外部接口返回字段不稳定，会直接阻塞后续阶段。
- 若首版需要后端代业务调用，必须额外评估 APPKEY 的存储与脱敏方案。
- 不建议在该阶段引入复杂权限体系，先保证身份链路稳定。
