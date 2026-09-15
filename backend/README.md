# 知识库管理平台后端

后端采用 FastAPI、LangGraph 和分层架构，外部能力通过 `domain/ports.py` 中的 Protocol 定义，并在 `infrastructure/adapters` 中提供具体实现。

## Architecture

```text
api            -> HTTP 路由、Schema、依赖注入
services       -> 用例编排
engines        -> LangGraph 知识维护、问答、入库和 FAQ/缺口流程
domain         -> 领域模型、Protocol 端口和纯业务规则
infrastructure -> MySQL、Redis、MinIO、Milvus、MinerU、VLM、LLM 和 Reranker 适配器
bootstrap      -> 配置与统一依赖容器
workers        -> 基于 MySQL 任务表的 Worker 与调度器
```

依赖方向：

```text
api -> services -> engines -> domain
infrastructure -> implements domain ports
bootstrap -> composition root
```

## External Services

- 文档解析：线上 MinerU API，PDF/Word 转为 Markdown，并抽取图片。
- 图片理解：OpenAI 兼容 VLM，摘要写回检索切片。
- 对象存储：MinIO，保存原始文档、Markdown 和图片。
- Embedding：默认使用本地 `BAAI/bge-m3`，也可配置远程 OpenAI 兼容接口。
- 向量与关键词检索：Milvus Dense Vector + BM25，两路检索后 RRF 融合。
- 最终重排：`TEXT_RERANK_*` 配置的 Reranker。
- HyDE 与回答生成：LangChain `ChatOpenAI`，通过 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `LLM_DEFAULT_MODEL` 配置。
- 缓存与任务：Redis 缓存，MySQL 任务表，不依赖 Celery、RabbitMQ。

## Run

```powershell
cd backend
uv sync --extra local-embedding
Copy-Item .env.example .env
uv run uvicorn kb_manage_platform.main:app --reload --host 0.0.0.0 --port 8000
```

Worker：

```powershell
cd backend
uv run python -m kb_manage_platform.workers.main
```

## Database

```powershell
mysql -u root -p < migrations/001_knowledge_maintenance.sql
mysql -u root -p < migrations/002_qa_and_identity.sql
mysql -u root -p < migrations/003_faq_gap_closed_loop.sql
mysql -u root -p < migrations/004_iam_auth_and_permissions.sql
```

## Import

提交已上传到 MinIO 的对象：

```text
POST /api/v1/import
```

上传文件并自动写入 MinIO：

```text
POST /api/v1/import/files
```

支持 `PDF`、`DOC`、`DOCX`、`MD`、`MARKDOWN`、`TXT`。

## Test

```powershell
cd backend
uv run pytest -q
uv run python -m compileall -q kb_manage_platform
```