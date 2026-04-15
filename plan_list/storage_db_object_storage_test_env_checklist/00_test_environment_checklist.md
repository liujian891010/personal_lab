# 测试环境配置清单

## 1. MySQL

- [ ] `MYSQL_HOST`
- [ ] `MYSQL_PORT`
- [ ] `MYSQL_DATABASE`
- [ ] `MYSQL_USERNAME`
- [ ] `MYSQL_PASSWORD`
- [ ] 确认字符集使用 `utf8mb4`
- [ ] 确认是否允许应用自动建表和自动迁移
- [ ] 确认应用账号至少具备 `SELECT` / `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `ALTER` / `INDEX`

## 2. MinIO

- [ ] `MINIO_ENDPOINT`
- [ ] `MINIO_PORT`
- [ ] `MINIO_BUCKET`
- [ ] `MINIO_ACCESS_KEY`
- [ ] `MINIO_SECRET_KEY`
- [ ] `MINIO_USE_SSL`
- [ ] `MINIO_REGION`
- [ ] 确认 bucket 已创建
- [ ] 确认应用账号对 bucket 具备读写权限
- [ ] 确认对象 key 规范采用 `workspaces/{userId}/{module}/{relative_path}`

## 3. APPKEY 登录

- [ ] `APPKEY_LOGIN_URL`
- [ ] `APPKEY_QUERY_PARAM`
- [ ] `APPKEY_APP_CODE`
- [ ] 准备至少 2 个测试 APPKEY
- [ ] 确认 2 个 APPKEY 返回不同 `userId`
- [ ] 确认返回字段至少包含 `userId` 和 `userName`

## 4. 应用基础配置

- [ ] `SESSION_SECRET`
- [ ] `APP_ENV=test`
- [ ] `LOG_LEVEL`
- [ ] `CORS_ALLOW_ORIGINS`
- [ ] 确认前端测试访问地址
- [ ] 确认后端测试访问地址

## 5. 存储与容量规则

- [ ] 单文件上限：`100MB`
- [ ] 单用户总容量：`5GB`
- [ ] 单用户文件数量：`2000`
- [ ] 支持类型：`md` / `txt` / `html` / `pdf` / `docx`
- [ ] PDF OCR 最大页数：`20`

## 6. 删除与清理规则

- [ ] 启用软删除
- [ ] MinIO 延迟删除：`7 天`
- [ ] 失败临时文件保留：`3 天`
- [ ] 审计日志保留上传 / 删除 / 重试 / 清理动作

## 7. 测试验收数据

- [ ] 用户 A 的测试 APPKEY
- [ ] 用户 B 的测试 APPKEY
- [ ] `md` 测试文件
- [ ] `pdf` 测试文件
- [ ] `docx` 测试文件
- [ ] 中文文件名测试文件
- [ ] 接近容量上限的大文件测试样本

## 8. 测试环境验收标准

- [ ] 用户 A 看不到用户 B 数据
- [ ] 上传文件成功写入 MinIO
- [ ] 元数据成功写入 MySQL
- [ ] 报告生成成功
- [ ] wiki / 检索链路正常
- [ ] 删除后进入软删除状态
- [ ] 清理任务可按规则删除对象
- [ ] 服务重启后数据仍可读
