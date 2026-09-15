# 前端按钮与后端 API 生效核对表

## 1. 核对范围

- 技术栈：Vue 3 + Vite + Element Plus + pdf.js
- API 前缀：/api/v1
- 核对方式：源码事件处理 + API 定义 + 后端路由 + TypeScript/Vite 生产构建
- 构建结果：通过
- 前端容器：HTTP 200

## 2. 登录与密码

| 页面 | 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- | --- |
| 登录页 | 登录 | login() | POST /auth/login | 已生效 |
| 修改密码 | 确认修改 | authApi.changePassword() | POST /auth/change-password | 已生效 |
| 顶部栏 | 退出 | logout() | POST /auth/logout | 已生效 |

## 3. 智能问答与会话

| 页面 | 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- | --- |
| 智能问答 | 新会话 | newSession() | 前端本地状态 | 已生效 |
| 智能问答 | 发送 | send() | POST /query/stream | 已生效 |
| 智能问答 | 停止 | AbortController.abort() | 中断 SSE | 已生效 |
| 智能问答 | 推荐问题 | send(question) | POST /query/stream | 已生效 |
| 智能问答 | 重命名 | renameSession() | PATCH /sessions/{id} | 已生效 |
| 智能问答 | 删除 | 受控确认弹窗 -> deleteSession() | DELETE /sessions/{id} | 已修复 |
| 智能问答 | 引用卡片 | openCitation() | GET /knowledge/{id}/preview | 已生效 |
| 会话历史 | 查看会话 | route.push() | 无 API | 已生效 |
| 会话历史 | 重命名 | rename() | PATCH /sessions/{id} | 已生效 |
| 会话历史 | 删除 | 受控确认弹窗 -> remove() | DELETE /sessions/{id} | 已修复 |

## 4. 知识管理

| 页面 | 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- | --- |
| 知识台账 | 查询 | load() | GET /knowledge | 已生效 |
| 知识台账 | 新建知识 | create() | POST /knowledge | 已生效 |
| 知识台账 | 分类管理 | 打开分类弹窗 | GET /knowledge-categories | 已生效 |
| 知识台账 | 新增分类 | saveCategory() | POST /knowledge-categories | 已生效 |
| 知识台账 | 删除分类 | knowledgeApi.deleteCategory() | DELETE /knowledge-categories/{id} | 已生效 |
| 知识台账 | 导入 | 打开上传弹窗 | POST /knowledge/{id}/versions/upload | 已生效 |
| 知识台账 | 提交导入 | batchUpload() | 多文件版本上传 | 已生效 |
| 知识台账 | 详情 | route.push() | 无 API | 已生效 |
| 知识台账 | 批量发布 | bulk(publish) | POST /knowledge/{id}/publish | 已生效 |
| 知识台账 | 批量停用 | bulk(disable) | POST /knowledge/{id}/disable | 已生效 |
| 知识台账 | 批量删除 | 受控弹窗 -> bulkDelete() | DELETE /knowledge/{id} | 已生效 |
| 知识详情 | 预览 | openPreview() | GET /knowledge/{id}/preview | 已生效 |
| 知识详情 | 下载原文件 | download() | GET /knowledge/{id}/download | 已生效 |
| 知识详情 | PDF | openPdf() + PdfPreview | GET download + pdf.js 渲染 | 已生效 |
| 知识详情 | 编辑 | saveEdit() | PATCH /knowledge/{id} | 已生效 |
| 知识详情 | 权限配置 | savePermissions() | PUT /knowledge/{id}/permissions | 已生效 |
| 知识详情 | 发布 | knowledgeApi.publish() | POST /knowledge/{id}/publish | 已生效 |
| 知识详情 | 停用 | knowledgeApi.disable() | POST /knowledge/{id}/disable | 已生效 |
| 知识详情 | 回滚 | 受控弹窗 -> rollback() | POST /versions/{versionId}/rollback | 已生效 |
| 知识详情 | 删除 | 受控弹窗 -> removeKnowledge() | DELETE /knowledge/{id} | 已生效 |

## 5. 导入中心

| 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- |
| 提交导入 | upload() | POST /knowledge/{id}/versions/upload | 已生效 |
| 刷新任务 | refresh() | GET /import/jobs/{id} | 已生效 |
| 重试 | importApi.retry() | POST /import/jobs/{id}/retry | 已生效 |

## 6. 沉淀运营

| 页面 | 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- | --- |
| FAQ 候选 | 挖掘 FAQ | mine() | POST /faq/mine | 已生效 |
| FAQ 候选 | 发布 | review(approve) | POST /faq/review | 已生效 |
| FAQ 候选 | 驳回 | review(reject) | POST /faq/review | 已生效 |
| 已发布 FAQ | 编辑 | saveFaq() | PUT /faq/{id} | 已生效 |
| 已发布 FAQ | 停用/启用 | setPublishedStatus() | POST /faq/{id}/status | 已生效 |
| 知识缺口 | 检测 | detect() | POST /gaps/detect | 已生效 |
| 知识缺口 | 转建草稿 | saveGap() | POST /gaps/{id}/convert | 已生效 |
| 知识缺口 | 忽略 | resolveGap(ignore) | POST /gaps/{id}/status | 已生效 |

## 7. 数据洞察

| 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- |
| 刷新 | load() | GET /dashboard/overview | 已生效 |
| 时间范围 | watch -> load() | range_days 参数 | 已生效 |
| 部门筛选 | watch -> load() | department_id 参数 | 已生效 |

## 8. 审计日志

| 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- |
| 查询 | load() | GET /audit/logs | 已生效 |
| 刷新 | load() | GET /audit/logs | 已生效 |
| 导出 CSV | exportLogs() | GET /audit/export | 已生效 |

## 9. 组织与账号

| 页面 | 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- | --- |
| 部门 | 新增/编辑 | saveDept() | POST/PATCH /departments | 已生效 |
| 部门 | 停用/启用 | setDepartmentStatus() | POST /departments/{id}/status | 已生效 |
| 部门 | 删除 | 受控弹窗 -> removeDept() | DELETE /departments/{id} | 已生效 |
| 用户 | 新建/分配角色 | saveUser() | POST /users、PUT /users/{id}/roles | 已生效 |
| 用户 | 重置密码 | resetUserPassword() | POST /users/{id}/password-reset | 已生效 |
| 用户 | 停用/启用 | setUserStatus() | POST /users/{id}/status | 已生效 |
| 角色 | 新建/编辑权限 | saveRole() | POST /roles、PUT /roles/{id}/permissions | 已生效 |
| 角色 | 停用/启用 | setRoleStatus() | POST /roles/{id}/status | 已生效 |
| 角色 | 删除 | 受控弹窗 -> removeRole() | DELETE /roles/{id} | 已生效 |

## 10. 模型与系统

| 页面 | 按钮 | 事件处理 | 后端接口 | 状态 |
| --- | --- | --- | --- | --- |
| 模型接口 | 编辑 | saveModel() | PUT /system/model-configs/{type} | 已生效 |
| 模型接口 | 测试 | testModel() | POST /system/model-configs/{type}/test | 已生效 |
| 系统参数 | 编辑 | saveSetting() | PUT /system/settings/{key} | 已生效 |

## 11. 本次修复重点

1. React + Ant Design 已替换为 Vue 3 + Element Plus。
2. 所有静态 Modal.confirm 已替换为受控 el-dialog。
3. 会话历史页面增加删除和重命名按钮。
4. 知识删除、回滚、批量删除和 IAM 删除/重置密码均改为受控弹窗。
5. PDF 原文件新增 pdf.js 预览组件。
6. 生产构建通过，前端容器返回 HTTP 200。
