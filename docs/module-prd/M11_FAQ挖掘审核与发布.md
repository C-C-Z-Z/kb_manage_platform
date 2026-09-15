# M11 FAQ 挖掘、审核与发布 模块 PRD

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 模块编号 | M11 |
| 模块名称 | FAQ 挖掘、审核与发布 |
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
从问答日志中发现高频问题，生成候选 FAQ，经过审核后发布和缓存。

### 页面
- /operations 的 FAQ 候选页签
- /operations 的已发布 FAQ 页签

### 功能需求
- 按时间窗口挖掘 FAQ。
- 候选包含代表问题、推荐答案、频次、用户数、置信度和权限签名。
- 审核发布或驳回。
- 已发布 FAQ 支持编辑、停用和启用。
- FAQ 使用独立数据权限。
- 更新、停用或权限变更后缓存失效。
- 精确问题哈希匹配优先。

### API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | /api/v1/faq/mine | 挖掘候选 |
| GET | /api/v1/faq/candidates | 候选列表 |
| POST | /api/v1/faq/review | 发布或驳回 |
| GET | /api/v1/faq/published | 已发布列表 |
| PUT | /api/v1/faq/{faq_id} | 更新内容 |
| POST | /api/v1/faq/{faq_id}/status | 启用/停用 |

### 状态流转
```
candidate -> pending_review -> published
                           \-> rejected
published <-> disabled
```

### 验收标准
- FAQ 发布后可直接回答标准问题。
- 停用后不再命中。
- 更新标准问题后旧缓存失效。

---

## 4. 依赖与交付说明

- 本模块的接口均以 `/api/v1` 为统一前缀。
- 权限码、资源状态和接口字段发生变化时，必须同步更新总体 PRD、迁移和前端权限。
- 模块验收应同时覆盖成功路径、权限拒绝、参数错误和依赖异常。
- 示例数据或初始化模块发生变化时，必须保持固定 ID 和幂等性。
