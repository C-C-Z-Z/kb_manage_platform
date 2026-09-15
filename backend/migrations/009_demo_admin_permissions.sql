-- 演示环境：系统管理员启用全部业务功能入口

INSERT IGNORE INTO iam_role_permission (role_id, permission_code) VALUES
('role-system-admin', 'knowledge:create'),
('role-system-admin', 'knowledge:update'),
('role-system-admin', 'knowledge:publish'),
('role-system-admin', 'knowledge:disable'),
('role-system-admin', 'knowledge:permission:manage'),
('role-system-admin', 'knowledge:download'),
('role-system-admin', 'import:create'),
('role-system-admin', 'import:read'),
('role-system-admin', 'faq:manage'),
('role-system-admin', 'faq:read'),
('role-system-admin', 'gap:manage'),
('role-system-admin', 'gap:read');
