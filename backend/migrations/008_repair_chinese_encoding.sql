-- 修复历史中文数据并统一迁移客户端字符集

SET NAMES utf8mb4;

UPDATE iam_role SET name = '普通用户' WHERE role_id = 'role-user';
UPDATE iam_role SET name = '系统管理员' WHERE role_id = 'role-system-admin';
UPDATE iam_role SET name = '知识管理员' WHERE role_id = 'role-knowledge-admin';

UPDATE iam_permission SET name = '部门管理' WHERE permission_code = 'iam:department:manage';
UPDATE iam_permission SET name = '用户管理' WHERE permission_code = 'iam:user:manage';
UPDATE iam_permission SET name = '角色权限管理' WHERE permission_code = 'iam:role:manage';
UPDATE iam_permission SET name = '知识维护（兼容）' WHERE permission_code = 'knowledge:manage';
UPDATE iam_permission SET name = 'AI 问答' WHERE permission_code = 'qa:use';
UPDATE iam_permission SET name = 'FAQ 管理' WHERE permission_code = 'faq:manage';
UPDATE iam_permission SET name = '知识缺口管理' WHERE permission_code = 'gap:manage';
UPDATE iam_permission SET name = '看板查看' WHERE permission_code = 'dashboard:read';
UPDATE iam_permission SET name = '审计查看' WHERE permission_code = 'audit:read';
UPDATE iam_permission SET name = '查看知识' WHERE permission_code = 'knowledge:read';
UPDATE iam_permission SET name = '创建知识' WHERE permission_code = 'knowledge:create';
UPDATE iam_permission SET name = '维护知识' WHERE permission_code = 'knowledge:update';
UPDATE iam_permission SET name = '发布知识' WHERE permission_code = 'knowledge:publish';
UPDATE iam_permission SET name = '停用或归档知识' WHERE permission_code = 'knowledge:disable';
UPDATE iam_permission SET name = '配置知识权限' WHERE permission_code = 'knowledge:permission:manage';
UPDATE iam_permission SET name = '导入文档' WHERE permission_code = 'import:create';
UPDATE iam_permission SET name = '查看导入任务' WHERE permission_code = 'import:read';
UPDATE iam_permission SET name = '查看问答历史' WHERE permission_code = 'qa:session:read';
UPDATE iam_permission SET name = '查看 FAQ' WHERE permission_code = 'faq:read';
UPDATE iam_permission SET name = '查看知识缺口' WHERE permission_code = 'gap:read';
UPDATE iam_permission SET name = '模型配置管理' WHERE permission_code = 'model:manage';
UPDATE iam_permission SET name = '系统参数管理' WHERE permission_code = 'system:manage';
UPDATE iam_permission SET name = '审计导出' WHERE permission_code = 'audit:export';
UPDATE iam_permission SET name = '知识原文件下载' WHERE permission_code = 'knowledge:download';

UPDATE knowledge_category SET name = '财务制度', description = '财务、报销、预算相关制度' WHERE category_id = 'finance';
UPDATE knowledge_category SET name = '人力资源', description = '人事、薪酬、考勤和员工制度' WHERE category_id = 'hr';
UPDATE knowledge_category SET name = '产品与研发', description = '产品、研发和项目规范' WHERE category_id = 'product';
UPDATE knowledge_category SET name = '运营管理', description = '运营流程与服务规范' WHERE category_id = 'operation';
UPDATE knowledge_category SET name = '通用制度', description = '公司通用规章制度' WHERE category_id = 'general';

UPDATE iam_department SET name = '总公司' WHERE department_id = 'dept-root';
UPDATE iam_department SET name = '人力资源部' WHERE department_id = 'dept-hr';
UPDATE iam_department SET name = '产品研发部' WHERE department_id = 'dept-product';

UPDATE knowledge_unit
SET title = '差旅报销示例知识', tags = JSON_ARRAY('财务', '差旅', '示例')
WHERE knowledge_id = 'knowledge-demo-travel';
