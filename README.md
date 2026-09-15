# 知识库管理平台

项目使用一个统一应用镜像承载前端、后端和 Worker；MySQL、Redis、MinIO、Milvus、etcd 等有状态服务继续使用官方镜像。

## 目录

- `frontend/`：Vue 3 + TypeScript + Vite + Element Plus 控制台，PDF 预览使用 pdf.js。
- `backend/`：FastAPI、LangGraph、MySQL、Redis、MinIO、Milvus 分层后端。
- `backend/migrations/`：可重复执行的数据库结构和权限初始化 SQL。
- `Dockerfile.app`：统一应用镜像，包含 Vue 前端静态文件、FastAPI 后端和 Worker 代码。
- `compose.yaml`：统一应用镜像与 MySQL、Redis、MinIO、Milvus、etcd、Attu 等有状态基础设施。
- `docs/acceptance-phase-a.md`：阶段 A 人工验收清单。

## 启动

1. 复制环境模板：

```powershell
Copy-Item backend\.env.example backend\.env
```

2. 填写 `backend\.env` 中的 MySQL、Redis、MinIO、JWT、Seed 密码，以及 MinerU、LLM、VLM、Embedding、Reranker 配置。不要提交真实密钥。

3. 启动全部服务：

```powershell
docker compose --env-file backend\.env up --build
```

4. 打开 `http://localhost:8080`，使用 `backend\.env` 中的 `SEED_ADMIN_USERNAME` 和 `SEED_ADMIN_PASSWORD` 登录。

## 服务端口

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://localhost:8080` |
| 后端 API | `http://localhost:8000/api/v1` |
| MinIO API | `http://localhost:9000` |
| MinIO 控制台 | `http://localhost:9001` |
| Attu | `http://localhost:8088` |

MySQL、Redis、Milvus、etcd 默认只在 Compose 网络内可达。需要本机调试时使用：

```powershell
docker compose --env-file backend\.env -f compose.yaml -f compose.dev.yaml up --build
```

## 外部 AI 服务

Compose 默认不容器化 MinerU、LLM、VLM、Reranker 和 Embedding。它们通过 `backend\.env` 中的 OpenAI 兼容接口调用。阶段 A 的问答协议保持单个 `delta` 事件，前端执行字符动画；阶段 B 可无修改前端协议地替换为真实 token 流。

## 周期任务

Worker 启动后会同时运行 MySQL 任务消费者和周期调度器。调度器默认每天投递一次 FAQ 挖掘与知识缺口检测任务，并通过 `background_job.idempotency_key` 保证同一时间片只执行一次。

可在 `backend\.env` 中分别控制：

```dotenv
SCHEDULER_ENABLED=true
SCHEDULER_POLL_INTERVAL_SECONDS=30
SCHEDULER_FAQ_MINING_INTERVAL_SECONDS=86400
SCHEDULER_FAQ_MINING_WINDOW_DAYS=30
SCHEDULER_GAP_DETECTION_INTERVAL_SECONDS=86400
SCHEDULER_GAP_DETECTION_WINDOW_DAYS=30
```

将对应的 `*_INTERVAL_SECONDS` 设为 `0` 可单独关闭该周期任务；`SCHEDULER_ENABLED=false` 可关闭整个调度器。
## 数据库与 Seed

- `db-init` 顺序执行 `backend/migrations/*.sql`，所有脚本均可重复执行。
- `seed` 独立容器负责幂等创建权限、角色、部门、管理员和演示数据。
- `SEED_DEMO_DATA=false` 时只创建必要管理员数据。
- Schema 以 SQL 迁移为事实源，应用启动不会执行 `create_all`。

## 本机开发校验

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q kb_manage_platform

cd ..\frontend
npm.cmd run build
```

## 安全说明

- 除 `/health`、`/auth/login` 外，接口均要求 Bearer JWT。
- 客户端不能提交 `user_id` 或 `operator_id` 覆盖身份。
- access token 只保存在前端内存，刷新页面会退出登录。
- 仓库内不应写入真实凭据。历史 `env.txt`、`backend/.env` 中的暴露密钥应尽快轮换。
