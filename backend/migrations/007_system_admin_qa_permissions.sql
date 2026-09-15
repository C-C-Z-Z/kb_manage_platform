-- 系统管理员默认具备 AI 对话与会话历史入口

INSERT IGNORE INTO iam_role_permission (role_id, permission_code) VALUES
('role-system-admin', 'qa:use'),
('role-system-admin', 'qa:session:read');
