# 演示样例文件使用指南

本目录提供一组可直接上传的演示文档，覆盖项目要求（`知识库管理平台项目要求.md` §2.9）中定义的四个核心演示场景。

所有内容均为**虚构的演示数据**，仅用于功能验证，不涉及真实企业制度。

---

## 一、文件清单

| 文件 | 格式 | 建议分类 | 建议数据权限 | 演示用途 |
| --- | --- | --- | --- | --- |
| `01-差旅报销标准.md` | Markdown | 财务制度 `finance` | **全局公开** | 场景一正面：全员可查 |
| `02-高管薪酬与股权激励细则.docx` | Word | 人力资源 `hr` | **部门 = 人力资源部** + **角色 = 知识管理员** | 场景一反面：越权拦截 |
| `03-生鲜食品破损退款政策.md` | Markdown | 运营管理 `operation` | **全局公开** | 场景二：高频 FAQ 沉淀素材 |
| `04-海外直邮保税仓清关说明.txt` | 纯文本 | 运营管理 `operation` | **全局公开** | 场景三：知识缺口补充文档（**先不导入**） |
| `05-办公用品领用流程-v1.md` | Markdown | 通用制度 `general` | 全局公开或按需 | 场景四：旧版本 |
| `05-办公用品领用流程-v2.md` | Markdown | 通用制度 `general` | 全局公开或按需 | 场景四：新版本（验证回滚） |
| `批量导入样例/印章使用管理规定.md` | Markdown | 通用制度 `general` | 全局公开 | 场景五：批量导入 |
| `批量导入样例/员工培训学时要求.txt` | 纯文本 | 人力资源 `hr` | 全局公开 | 场景五：批量导入 |
| `批量导入样例/员工入职与试用期管理规定.md` | Markdown | 人力资源 `hr` | 全局公开 | 场景五：批量导入 |

---

## 二、环境与账号前置准备

### 2.1 启动环境

```powershell
cd <项目根目录>
docker compose up -d
# 等待 backend 健康检查通过
curl http://localhost:8000/api/v1/health
```

`compose.yaml` 中 `seed` 服务会幂等写入部门、角色、管理员与演示账号。
若需演示数据（`kbadmin` / `demo` 账号、看板基线、示例知识），确认 `backend/.env` 中：

```ini
SEED_DEMO_DATA=true
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=<自定义密码>
```

### 2.2 内置账号

| 账号 | 所属部门 | 角色 | 可用能力 | 登录密码 |
| --- | --- | --- | --- | --- |
| `admin` | 总公司 | 系统管理员 | 全部功能（含组织、角色、模型配置、审计） | `backend/.env` 的 `SEED_ADMIN_PASSWORD` |
| `kbadmin` | 产品研发部 | 知识管理员 | 知识维护、导入、FAQ/缺口管理、问答、看板 | 同上 |
| `demo` | 产品研发部 | 普通用户 | 仅 AI 问答与会话历史 | 同上 |

> 三个账号密码相同，均由 `SEED_ADMIN_PASSWORD` 决定。

### 2.3 内置部门 / 角色 / 分类

| 类型 | 可选值 |
| --- | --- |
| 部门 | 总公司 `dept-root`、人力资源部 `dept-hr`、产品研发部 `dept-product` |
| 角色 | 系统管理员 `role-system-admin`、知识管理员 `role-knowledge-admin`、普通用户 `role-user` |
| 分类 | 财务制度 `finance`、人力资源 `hr`、产品与研发 `product`、运营管理 `operation`、通用制度 `general` |

---

## 三、演示场景

### 场景一：四维数据权限隔离（跨部门财务与薪酬）

对应项目要求 §2.9.9 场景一，验证「默认拒绝 + OR 判定 + 越权不泄漏」。

**操作步骤**

1. 以 `kbadmin` 登录，进入**知识维护与导入中心**。
2. 上传 `01-差旅报销标准.md`：
   - 分类选「财务制度」，标题填「差旅报销标准」；
   - 进入权限配置弹窗，勾选 **全局公开**；
   - 提交后点击**发布**，等待解析与向量化进度到 100%。
3. 上传 `02-高管薪酬与股权激励细则.docx`：
   - 分类选「人力资源」，标题填「高管薪酬与股权激励细则」；
   - 权限配置勾选 **部门 → 人力资源部**，并追加 **角色 → 知识管理员**；
   - 提交后点击**发布**，等待索引进度到 100%。
   - 注意：此处不要勾选全局公开，保持其他权限为空。
4. 以 `demo` 登录，进入**AI 智能问答工作台**，依次提问：
   - 「出差住宿费标准是多少？」→ 应正常回答并返回引用来源卡片。
   - 「高管薪酬由哪几部分组成？」→ 应**无法获得答案**。
   - 「股权激励的行权价格怎么确定？」→ 应**无法获得答案**。
5. 退出，改用 `kbadmin` 登录，再次提问「高管薪酬由哪几部分组成？」→ 此时应正常回答并给出引用来源。

**预期结果**

| 提问账号 | 提问内容 | 命中的知识 | 结果 |
| --- | --- | --- | --- |
| `demo` | 出差住宿费标准 | 差旅报销标准（全局公开） | 正常回答 + 引用 |
| `demo` | 高管薪酬 / 股权激励 | 高管薪酬细则（部门 + 角色） | 被拦截，不返回内容 |
| `kbadmin` | 高管薪酬 / 股权激励 | 高管薪酬细则（角色命中） | 正常回答 + 引用 |

**权限命中原因为什么成立**

- `demo` 属于「产品研发部」+「普通用户」：既不是人力资源部，也没有知识管理员角色 → 两条规则均不命中 → 拒绝。
- `kbadmin` 属于「产品研发部」+「知识管理员」：部门不命中，但**角色命中** → OR 逻辑放行。
- 全平台默认无公开权限，因此「不配置任何权限」= 谁都看不到。

**如需完全复刻 PRD 的「管理层角色」写法**

内置角色没有「管理层」。用 `admin` 登录系统配置页新建角色「管理层」（勾选 `qa:use` 与 `knowledge:read`），新建一个归属「人力资源部」的账号并授予该角色，即可得到与 PRD 描述完全一致的演示效果。

**越权拦截的两种可见证据**

1. **审计日志**（`admin` → 审计日志页，或 `GET /api/v1/audit/logs`）：检索 `qa.completed` 事件，可见 `recall_count > 0` 而 `blocked_count > 0`、`final_count = 0`，`blocked_knowledge_ids` 中列出被拦截的知识 ID —— 证明「文件被检索到了，但被权限挡住了」。
2. **回答内容**：不返回任何薪酬细节，回退为「现有知识无法支撑该问题。」

> ⚠️ **已知差异**：PRD §2.9.4 要求回答中显式提示「部分参考资料因权限受限无法展示」。当前版本该提示**尚未接入回答输出**（拦截数据已写入审计，但没有透传到 `AnswerResult.warnings`）。演示时请以审计日志中的 `blocked_count` 作为拦截证据。修复建议见 `docs/后端项目总结.md` §7.1①。

---

### 场景二：高频问答沉淀为 FAQ 与缓存加速

对应项目要求 §2.9.9 场景二前半段，验证「聚类挖掘 → 人工审核 → 缓存直出」。

**操作步骤**

1. 以 `kbadmin` 登录，上传并**发布** `03-生鲜食品破损退款政策.md`（分类「运营管理」，权限全局公开）。
2. 制造高频提问日志。**触发 FAQ 候选的阈值是「同一问题出现 ≥10 次」且「≥5 个不同用户」**（`FaqGapCommand` 的固定默认值，接口不可调）。内置账号只有 `admin` / `kbadmin` / `demo` 三个，**手动提问无法凑够 5 个不同用户**，因此推荐直接用 §六.1 的 SQL 批量造日志。
3. 进入**知识沉淀与运营管理页 → FAQ 挖掘与审核发布区**，点击「触发挖掘」（或调用 `POST /api/v1/faq/mine`，`window_days` 填 30）。
4. 候选列表中应出现「生鲜食品破损如何申请退款」，展示聚合频次与推荐标准答案。
5. 点击**采纳并编辑**，确认标准问题与答案后**发布**。
6. 回到问答工作台，**用完全相同的问法**再问一次「生鲜食品破损如何申请退款？」→ 应毫秒级返回标准答案。

**预期结果**

挖掘完成后按下表分流，两条路径都是设计预期：

| 候选的 `permission_signature` | 是否命中敏感词 | 候选状态 | 后续动作 |
| --- | --- | --- | --- |
| `global` | 否 | `candidate` → **自动发布** | 无需人工介入，挖掘即上线 |
| `global` | 是 | `pending_review` | 转人工审核 |
| `mixed` / 其他（默认 SQL 走这条） | — | `pending_review` | 转人工审核 |

- 走人工审核时，在 FAQ 审核发布区采纳并编辑标准问答后发布，即写入独立权限并清理旧缓存。
- 发布后走 `RedisFaqCache`，相同问题直接命中缓存，**不再调用大模型**；缓存键为 `faq:answer:{问题哈希}:{用户}:{部门}:{角色哈希}:{权限版本}`，按用户维度隔离。
- 在已发布 FAQ 区可对问答对做编辑与启停，启停后缓存同步失效。

> ⚠️ **两个必须知道的细节**
>
> **1）FAQ 匹配是「规范化后精确匹配」，不是语义匹配。** 缓存键由 `question_hash()`（去空白 + 统一小写）生成，所以「生鲜食品破损如何申请退款？」与「水果坏了怎么退钱？」虽然语义相同，**不会命中同一条 FAQ 缓存**。演示时必须使用与已发布标准问题**完全一致**的问法（因此 SQL 里的 `question` 字段写了标准问法）。
>
> **2）推荐阈值当前不可通过接口调整。** `min_occurrences=10`、`min_users=5` 是 `FaqGapCommand` 的固定默认值，接口只暴露 `window_days`。所以必须用 §六.1 的 SQL 造出「12 条日志 / 5 个不同用户」才看得到候选。

---

### 场景三：知识缺口识别与补充闭环

对应项目要求 §2.9.9 场景二后半段，验证「未命中提问 → 缺口池 → 转建 → 发布后自动关闭」。

**操作步骤**

1. **先不要导入** `04-海外直邮保税仓清关说明.txt`（当前知识库中没有任何清关相关内容）。
2. 用任意账号提问以下**知识库中不存在**的问题，重复若干次：
   - 「海外直邮保税仓清关延误怎么办？」
   - 「保税仓发货为什么还要身份证？」
   - 「报关申报失败会被扣货吗？」
3. 进入**知识沉淀与运营管理页 → 知识缺口清单区**，点击「检测缺口」（或 `POST /api/v1/gaps/detect`）。
4. 缺口列表中应出现上述问题，带频次、涉及部门、最高相似度与建议分类，类型为 `no_candidate`（完全未命中）。
5. 在缺口项上点击**一键转建为知识补充任务** → 生成知识补充草稿（状态转为 `converted`）。
6. 到知识维护中心，导入 `04-海外直邮保税仓清关说明.txt` 并**发布**。
7. 回到缺口清单 → 该缺口状态应自动变为 `resolved`。

**预期结果**

| 阶段 | 缺口状态 | 触发方式 |
| --- | --- | --- |
| 检测出问题 | `pending` | `POST /api/v1/gaps/detect` |
| 一键转建草稿 | `converted` | `POST /api/v1/gaps/{gap_id}/convert` |
| 补充知识发布 | `resolved` | 发布时自动调用 `resolve_by_knowledge()` |

**另一种缺口类型 `low_confidence`**：当知识被召回但**全部被权限拦截**时也会归入缺口池（判定条件 `authorized_count > 0 且 final_count = 0`）。可复用场景一中 `demo` 提问高管薪酬的那几条日志来演示。

---

### 场景四：知识版本管理与回滚

验证多版本上传与「回滚后检索内容随之变化」。

**操作步骤**

1. 以 `kbadmin` 登录，新建知识单元，标题「办公用品领用流程」，分类「通用制度」。
2. 上传 `05-办公用品领用流程-v1.md` 作为首个版本，发布，等待索引完成。
3. 在问答工作台提问「办公用品每月能领多少钱？」→ 应回答 **200 元**（V1 内容）。
4. 回到知识详情页，**上传新版本** `05-办公用品领用流程-v2.md`，发布，等待索引完成。
5. 再次提问同一问题 → 应回答 **350 元**（V2 内容）。
6. 打开版本列表，对 V1 执行**回滚**（`POST /api/v1/knowledge/{id}/versions/{version_id}/rollback`）。
7. 第三次提问 → 应重新回答 **200 元**。

**预期结果**

- 版本列表中可看到两个版本及其状态（`indexed` / `superseded`）。
- 回滚通过切换知识单元的 `current_version_id` 实现，鉴权引擎在检索时会校验「命中版本必须是当前版本」，因此回滚即时生效，无需重刷向量索引。

---

### 场景五：批量导入与多格式解析

验证文件夹拖拽批量导入与多格式解析链路。

**操作步骤**

1. 以 `kbadmin` 登录，进入知识维护与导入中心，使用**批量拖拽导入**。
2. 一次性拖入 `批量导入样例/` 下的 3 个文件（Markdown + 纯文本混合）。
3. 观察导入抽屉中的解析与向量化进度条逐条推进。
4. 导入完成后，在台账列表中确认三条知识的格式、分类、权限标签与状态。
5. 逐条配置数据权限并发布，然后在问答工作台验证可检索：
   - 「印章可以带出办公场所吗？」
   - 「年度培训学时要求是多少？」
   - 「试用期最长多久？」

**预期结果**

- 三个文件均被正确解析、切片并写入 Milvus。
- Markdown 文档的标题层级被识别为 `section_path`，纯文本文档按段落切分。
- 台账列表展示格式列（`markdown` / `text`）。

---

## 四、格式解析覆盖矩阵

系统支持 `PDF` / `DOC` / `DOCX` / `MD` / `MARKDOWN` / `TXT`，本目录覆盖情况：

| 格式 | 本目录文件 | 解析链路 |
| --- | --- | --- |
| `.md` | `01`、`03`、`05-v1`、`05-v2`、`批量导入样例/印章使用管理规定.md`、`批量导入样例/员工入职与试用期管理规定.md` | 直接读取文本 → 按 Markdown 结构切片 |
| `.txt` | `04`、`批量导入样例/员工培训学时要求.txt` | 直接读取文本 → 按段落切片 |
| `.docx` | `02-高管薪酬与股权激励细则.docx` | MinerU 解析 → Markdown → VLM 图片摘要 → 切片 |
| `.pdf` / `.doc` | 未提供 | 如需演示，用 Word / WPS 将 `02` 另存为 PDF 或 `.doc` 即可复用同一场景 |

`02` 的 Word 文档通过 `python-docx` 生成，含标题层级（Heading 0/1）与正文段落共 48 段，可验证 MinerU 对 Word 样式的识别效果。

---

## 五、演示提问语句清单

可直接复制用于演示，按预期结果分组。

**应正常回答（有权限命中）**

```
出差住宿费标准是多少？
差旅报销需要提交哪些材料？
报销申请需要在多久内提交？
生鲜食品破损如何申请退款？
退款申请后多久能到账？
国外出差有单独的补贴标准吗？
印章可以带出办公场所吗？
年度培训学时要求是多少？
试用期最长多久？
```

**应被权限拦截（用于场景一反面）**

```
高管薪酬由哪几部分组成？
股权激励的行权价格怎么确定？
竞业限制期间有补偿吗？
年度绩效奖金的系数区间是多少？
```

**应进入知识缺口池（用于场景三）**

```
海外直邮保税仓清关延误怎么办？
保税仓发货为什么还要身份证？
报关申报失败会被扣货吗？
```

---

## 六、演示加速技巧

### 6.1 批量造问答日志（用于 FAQ 挖掘与缺口检测）

手动提问凑够 10 次 / 5 人比较费时（内置仅 3 个账号），可直接向 `qa_audit` 表写入 `qa.completed` 事件。FAQ 挖掘与缺口检测都从该表读取。

**造 FAQ 候选用的高频日志**（`recall_count > 0` 且 `final_count > 0`，即正常命中）：

```sql
-- 12 条日志，来自 5 个不同 user_id，满足 min_occurrences=10 与 min_users=5
-- permission_signatures 留空 → 签名判定为 mixed → 候选进入「待人工审核」
INSERT INTO qa_audit (event_type, request_id, user_id, payload)
SELECT 'qa.completed',
       CONCAT('demo-faq-', n),
       ELT(1 + (n % 5), 'user-demo', 'user-kbadmin', 'user-admin', 'user-demo-2', 'user-demo-3'),
       JSON_OBJECT(
         'request_id', CONCAT('demo-faq-', n),
         'user_id', ELT(1 + (n % 5), 'user-demo', 'user-kbadmin', 'user-admin', 'user-demo-2', 'user-demo-3'),
         'department_id', 'dept-product',
         'question', '生鲜食品破损如何申请退款？',
         'recall_count', 5,
         'authorized_count', 5,
         'final_count', 3,
         'answer_excerpt', '签收后 48 小时内提交申请，上传破损照片，按破损比例退款。',
         'permission_signatures', JSON_ARRAY()
       )
FROM (SELECT 1 n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
      UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
      UNION SELECT 11 UNION SELECT 12) t;
```

> `user-demo-2` / `user-demo-3` 是**不存在的虚拟用户**，仅用于满足「≥5 个不同用户」的聚类条件。`qa_audit.user_id` 无外键约束，不影响 FAQ 挖掘。副作用：看板做**部门维度**筛选时，这两个虚拟用户会被 `iam_user` 关联查询过滤掉，因此部门口径的 PV/UV 会略低于总量口径——这是预期行为，不影响 FAQ 演示。

**变体：演示「全局 FAQ 自动发布」**

把上面 SQL 中的 `'permission_signatures', JSON_ARRAY()` 改为 `JSON_ARRAY('global')`，再重新执行挖掘，即可看到另一条链路：候选签名判定为 `global` 且未命中敏感词时，`NodeMineFaq` 会**直接调用 `publish_candidate` 自动上线**（授予全局权限并清理缓存），候选状态直接变为 `published`，无需人工审核。

> 想验证敏感词拦截，可在 `backend/.env` 的 `FAQ_SENSITIVE_KEYWORDS` 中填入一个出现在标准答案里的词（如 `退款`），此时即使签名是 `global` 也会被降级为 `pending_review` 等待人工审核。

**造知识缺口用的未命中日志**（`recall_count = 0`）：

```sql
INSERT INTO qa_audit (event_type, request_id, user_id, payload)
SELECT 'qa.completed', CONCAT('demo-gap-', n), 'user-demo',
       JSON_OBJECT(
         'request_id', CONCAT('demo-gap-', n),
         'user_id', 'user-demo',
         'department_id', 'dept-product',
         'question', '海外直邮保税仓清关延误怎么办？',
         'recall_count', 0,
         'authorized_count', 0,
         'final_count', 0,
         'answer_excerpt', '现有知识无法支撑该问题。',
         'permission_signatures', JSON_ARRAY()
       )
FROM (SELECT 1 n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
      UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) t;
```

写入后调用 `POST /api/v1/faq/mine` 与 `POST /api/v1/gaps/detect` 即可看到候选与缺口。

### 6.2 常用接口速查

```text
取 token        POST /api/v1/auth/login
上传文件        POST /api/v1/import/files            （multipart: file）
提交已有对象    POST /api/v1/import
查询任务进度    GET  /api/v1/import/jobs/{job_id}
重试失败任务    POST /api/v1/import/jobs/{job_id}/retry
配置知识权限    PUT  /api/v1/knowledge/{id}/permissions
发布知识        POST /api/v1/knowledge/{id}/publish
回滚版本        POST /api/v1/knowledge/{id}/versions/{version_id}/rollback
问答            POST /api/v1/query
流式问答        POST /api/v1/query/stream
FAQ 挖掘        POST /api/v1/faq/mine
FAQ 候选列表    GET  /api/v1/faq/candidates
FAQ 审核发布    POST /api/v1/faq/review
缺口检测        POST /api/v1/gaps/detect
缺口转建        POST /api/v1/gaps/{gap_id}/convert
看板指标        GET  /api/v1/dashboard/overview
审计日志        GET  /api/v1/audit/logs
```

---

## 七、演示前必读的三个行为细节

1. **默认拒绝**：新建知识单元默认不公开（创建时只自动授予创建者本人权限）。未显式配置权限的知识，除创建者外任何人都检索不到，这属于设计预期而非缺陷。

2. **FAQ 缓存需精确匹配**：缓存键为规范化后的问题哈希。演示缓存命中时，必须与已发布 FAQ 的标准问题**逐字一致**。

3. **流式输出为整段返回**：`/query/stream` 当前在生成完整回答后一次性下发，前端看不到逐字打字效果。若演示脚本包含「流式打字机」环节，请提前说明或跳过。修复建议见 `docs/后端项目总结.md` §7.1③。

---

## 八、清理与重置演示数据

演示后可清理本次写入的数据（按外键顺序执行）：

```sql
-- 1. 清理演示造的问答日志
DELETE FROM qa_audit
 WHERE request_id LIKE 'demo-faq-%' OR request_id LIKE 'demo-gap-%';

-- 2. 清理缺口及其来源关联
DELETE FROM knowledge_gap_source
 WHERE request_id LIKE 'demo-gap-%';
DELETE FROM knowledge_gap
 WHERE representative_question LIKE '%清关%';

-- 3. 清理 FAQ 候选来源、候选（含自动发布产生的记录）
DELETE FROM knowledge_faq_candidate_source
 WHERE request_id LIKE 'demo-faq-%';
DELETE FROM knowledge_faq_candidate
 WHERE representative_question LIKE '%生鲜食品破损%';

-- 4. 若已走「自动发布」路径，还需清理已发布 FAQ 与其权限
DELETE FROM knowledge_faq_permission
 WHERE faq_id IN (SELECT faq_id FROM knowledge_faq WHERE standard_question LIKE '%生鲜食品破损%');
DELETE FROM knowledge_faq
 WHERE standard_question LIKE '%生鲜食品破损%';
```

> 若是「自动发布」路径，删除 `knowledge_faq` 后 Redis 中可能仍残留该问题的缓存条目。执行
> `docker exec -it kb-manage-platform-redis-1 redis-cli -a <REDIS_PASSWORD> FLUSHDB`
> 可彻底清空缓存（演示环境专用，勿在生产执行）。

知识单元建议通过前端**停用 / 归档**而非物理删除，以便保留审计轨迹。如需彻底重来，直接重建容器卷：

```powershell
docker compose down -v && docker compose up -d
```

> 注意：`down -v` 会删除 MySQL、Redis、MinIO、Milvus 的全部数据卷，需重新执行迁移与 seed。

---

## 附：相关文档

| 文档 | 内容 |
| --- | --- |
| `../知识库管理平台项目要求.md` | 需求原文与验收标准 |
| `../docs/后端项目总结.md` | 后端架构、技术栈、业务流程与待优化点 |
| `../docs/知识库管理平台PRD.md` | 产品需求细节 |
| `../docs/module-prd/` | 各模块（M01~M15）接口与交互说明 |
| `../docs/frontend-button-api-mapping.md` | 前端按钮与后端接口映射 |
