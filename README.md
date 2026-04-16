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
