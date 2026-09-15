-- 组织账号、JWT 认证和操作权限表（可重复执行）

DROP PROCEDURE IF EXISTS add_column_if_missing;
DELIMITER //
CREATE PROCEDURE add_column_if_missing(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND column_name = p_column_name
    ) THEN
        SET @ddl = CONCAT(
            'ALTER TABLE `', p_table_name, '` ADD COLUMN `', p_column_name, '` ', p_definition
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//
DELIMITER ;

CALL add_column_if_missing('iam_user', 'password_hash', 'VARCHAR(512) NULL');
UPDATE iam_user SET password_hash = '' WHERE password_hash IS NULL;
ALTER TABLE iam_user MODIFY COLUMN password_hash VARCHAR(512) NOT NULL DEFAULT '';
CALL add_column_if_missing('iam_user', 'failed_login_attempts', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_missing('iam_user', 'locked_until', 'DATETIME NULL');
CALL add_column_if_missing('iam_user', 'last_login_at', 'DATETIME NULL');
CALL add_column_if_missing('iam_user', 'created_at', 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP');
CALL add_column_if_missing('iam_user', 'updated_at', 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');
DROP PROCEDURE IF EXISTS add_column_if_missing;

CREATE TABLE IF NOT EXISTS iam_permission (
    permission_code VARCHAR(128) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    permission_type VARCHAR(32) NOT NULL,
    parent_code VARCHAR(128) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS iam_role_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id VARCHAR(64) NOT NULL,
    permission_code VARCHAR(128) NOT NULL,
    UNIQUE KEY uq_role_permission (role_id, permission_code),
    INDEX idx_role_permission_role (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO iam_permission (permission_code, name, permission_type, parent_code) VALUES
('iam:department:manage', '部门管理', 'api', ''),
('iam:user:manage', '用户管理', 'api', ''),
('iam:role:manage', '角色权限管理', 'api', ''),
('knowledge:manage', '知识维护（兼容）', 'api', ''),
('qa:use', 'AI 问答', 'api', ''),
('faq:manage', 'FAQ 管理', 'api', ''),
('gap:manage', '知识缺口管理', 'api', ''),
('dashboard:read', '看板查看', 'api', ''),
('audit:read', '审计查看', 'api', '');

INSERT IGNORE INTO iam_role (role_id, name, status) VALUES
('role-system-admin', '系统管理员', 'active'),
('role-knowledge-admin', '知识管理员', 'active'),
('role-user', '普通用户', 'active');

INSERT IGNORE INTO iam_role_permission (role_id, permission_code) VALUES
('role-system-admin', 'iam:department:manage'),
('role-system-admin', 'iam:user:manage'),
('role-system-admin', 'iam:role:manage'),
('role-system-admin', 'audit:read'),
('role-system-admin', 'dashboard:read'),
('role-knowledge-admin', 'knowledge:manage'),
('role-knowledge-admin', 'faq:manage'),
('role-knowledge-admin', 'gap:manage'),
('role-knowledge-admin', 'dashboard:read'),
('role-knowledge-admin', 'qa:use'),
('role-user', 'qa:use');

