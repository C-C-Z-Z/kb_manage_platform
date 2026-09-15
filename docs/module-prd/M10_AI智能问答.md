# M10 AI 智能问答 模块 PRD

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 模块编号 | M10 |
| 模块名称 | AI 智能问答 |
| 文档版本 | v1.0 |
| 目标读者 | 产品、研发、测试、运维、实施 |
| 上游依据 | 总体 PRD、模块级 PRD、现有代码与数据库迁移 |
| 文档状态 | 当前阶段可实现、可验收版本 |

## 2. 全局约束摘要

- 认证方式：Bearer JWT，默认有效期 8 小时。
- 权限模型：操作权限 RBAC + 知识四维数据权限。
- 四维权限：global、department、role、user，按 OR 逻辑组合。
- API 前缀：`/api/v1`。
- 后端分层：API / Service / Domain / Infrastructure / Bootstrap。
- 事实存储：MySQL、Redis、MinIO、Milvus。
- 本地向量模型：BGE-M3，默认 CPU，FP16=False。
- 所有知识访问必须实时执行数据权限校验。
- 密码、Token 和模型密钥不得写入日志。
- 固定示例数据必须使用稳定 ID，并支持幂等执行。

## 3. 模块需求

### 目标
提供多轮问答、授权混合检索、FAQ 快速命中、重排、受控生成、SSE、引用和权限提示。

### 页面
- /chat
- /sessions
- 引用知识预览弹窗

### 问答流程
```
问题 -> FAQ 精确匹配
  -> FAQ 语义命中
  -> Dense/BM25 混合检索
  -> RRF 融合
  -> Reranker
  -> 四维权限过滤
  -> 授权上下文
  -> LLM/FAQ 回答
  -> 会话与审计保存
```

### 功能需求
- 多轮会话，上下文默认最近 10 轮。
- 新会话和会话历史相互隔离。
- 重命名、删除自己的会话。
- SSE 事件包括 meta、delta、citation、warning、usage、done、error。
- 回答严格基于授权知识。
- 权限受限时显示“部分参考资料因权限受限无法展示”。
- 引用可再次点击预览并重新鉴权。
- FAQ 命中时直接返回标准答案。
- 向量不可用时降级关键词检索。

### API

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | /api/v1/query | qa:use | 非流式问答 |
| POST | /api/v1/query/stream | qa:use | SSE 问答 |
| GET | /api/v1/sessions | qa:session:read | 会话列表 |
| PATCH | /api/v1/sessions/{session_id} | qa:session:read | 重命名 |
| DELETE | /api/v1/sessions/{session_id} | qa:session:read | 删除 |
| GET | /api/v1/sessions/{session_id}/messages | qa:session:read | 消息与引用 |

### 验收标准
- 问题“年假如何申请？”可命中 FAQ。
- 问题“差旅报销需要哪些材料？”可召回示例知识并返回引用。
- 无权限知识不得进入上下文、回答、引用或 warning。
- 会话只能由所属用户读取和修改。

---

## 4. 依赖与交付说明

- 本模块的接口均以 `/api/v1` 为统一前缀。
- 权限码、资源状态和接口字段发生变化时，必须同步更新总体 PRD、迁移和前端权限。
- 模块验收应同时覆盖成功路径、权限拒绝、参数错误和依赖异常。
- 示例数据或初始化模块发生变化时，必须保持固定 ID 和幂等性。
