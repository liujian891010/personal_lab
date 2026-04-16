# personal_lab

## 项目简介

这是一个基于 FastAPI 的本地知识库 / 报告中心服务，前端静态页面由后端直接挂载并通过 `/app/` 提供访问。

## 启动这个服务需要什么环境

### 必须环境

- Python 3.11 或 3.12
- 本地磁盘可写权限
- 可用的 `8000` 端口
- 服务端可访问外部 APPKEY 登录接口

当前登录依赖的外部接口默认是：

```text
https://sg-al-cwork-web.mediportal.com.cn/user/login/appkey
```

### 当前不需要

- 不需要 Node.js / npm
- 不需要 MySQL
- 不需要 Redis
- 不需要 Nacos
- 不需要单独部署对象存储服务

当前版本默认使用本地文件系统和 SQLite。

## Python 依赖

仓库里当前声明的依赖位于 `backend/requirements.txt`：

- fastapi
- uvicorn
- pydantic
- python-multipart
- pypdf
- PyMuPDF
- rapidocr-onnxruntime
- python-docx
- beautifulsoup4

另外，代码中实际使用了 `python-dotenv`，建议一并安装：

```powershell
pip install python-dotenv
```

## 目录与存储

服务启动时会自动创建并使用以下目录：

- `data/`
- `logs/`
- `reports/`
- `uploads/`
- `raw/`
- `knowledge/`

数据库默认使用本地 SQLite 文件：

```text
data/reports.db
```

## 可选环境变量

如果不配置，项目会使用仓库内默认目录和默认登录接口。

常用可选环境变量：

- `DATA_ROOT`
- `RAW_ROOT`
- `REPORTS_ROOT`
- `UPLOADS_ROOT`
- `KNOWLEDGE_ROOT`
- `LOGS_ROOT`
- `SQLITE_PATH`
- `OBJECT_STORAGE_ROOT`
- `APPKEY_LOGIN_URL`
- `APPKEY_QUERY_PARAM`
- `APPKEY_APP_CODE`
- `AUTH_HTTP_TIMEOUT_SEC`
- `ADDITIONAL_REPORT_ROOTS`

`.env.example` 当前示例：

```env
ADDITIONAL_REPORT_ROOTS=%USERPROFILE%\.easyclaw\openclaw\workspace\arc-reactor-doc\wiki\sources
```

## 安装与启动

在项目根目录执行：

```powershell
pip install -r backend/requirements.txt
pip install python-dotenv
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

如果你希望开发时自动重载，可以使用：

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 启动后访问地址

- 工作台：`http://127.0.0.1:8000/app/`
- 健康检查：`http://127.0.0.1:8000/api/health`
- API 文档：`http://127.0.0.1:8000/docs`

## 一句话总结

当前项目是单机可运行架构，启动的关键前提只有四个：

- Python 环境可用
- 依赖包完整
- 本地目录可写
- 服务端能访问外部 APPKEY 登录接口

## 打包为 Wheel

如果你要把它提供给其他项目集成，建议直接发布 wheel，而不是交付源码目录。

安装 wheel 后，可通过控制台命令启动：

```powershell
personal-lab-server --host 127.0.0.1 --port 8000 --home .\runtime\personal_lab
```

说明：

- `--home` 用于指定运行时数据目录
- 源码模式默认写回当前仓库
- wheel 安装模式默认写到当前工作目录下的 `./.personal_lab`

建议集成方显式传入 `--home`，避免和宿主项目文件混在一起。

### 构建命令

```powershell
python -m build --wheel
```

构建完成后的 wheel 默认位于：

```text
dist/
```

## 其他项目集成方案

如果项目 A 需要在启动时顺带启动本服务，推荐把本服务作为独立 sidecar 进程，而不是直接把源码嵌入项目 A。

### 推荐集成方式

1. 项目 A 先检查健康接口：

```text
http://127.0.0.1:8000/api/health
```

2. 如果不可用，再启动本服务：

```powershell
personal-lab-server --host 127.0.0.1 --port 8000 --home .\runtime\personal_lab
```

3. 轮询健康接口，直到返回 `200`

4. 健康检查通过后，项目 A 再继续自己的初始化流程

### 为什么这样集成

- 解耦，项目 A 不需要感知本项目内部实现
- 便于升级，后续只需要替换 wheel 文件
- 便于隔离，把本项目的数据目录单独放到 `--home` 指定目录
- 便于排障，接口不可用时可以直接看本服务日志和健康检查

### 项目 A 需要固定的内容

- wheel 文件
- 启动命令
- 健康检查地址
- 单独的运行目录

建议约定如下：

- wheel：`personal_lab_service-0.1.0-py3-none-any.whl`
- 启动命令：`personal-lab-server --host 127.0.0.1 --port 8000 --home .\runtime\personal_lab`
- 健康检查：`http://127.0.0.1:8000/api/health`
- 工作台地址：`http://127.0.0.1:8000/app/`

### 集成方最小流程

```text
安装 wheel
-> 检查 /api/health
-> 未启动则拉起 personal-lab-server
-> 等待 /api/health 返回 200
-> 调用本服务 API 或打开 /app/
```

### 不推荐的方式

- 不推荐直接复制源码到项目 A
- 不推荐把本项目数据库和项目 A 的数据库强行合并
- 不推荐让项目 A 直接读写本项目内部数据目录

推荐始终通过 HTTP API 和本服务交互。
