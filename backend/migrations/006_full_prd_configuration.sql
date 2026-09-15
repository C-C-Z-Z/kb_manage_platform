-- 完整 PRD 功能补充：分类、模型配置、系统参数和权限

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

CALL add_column_if_missing('iam_department', 'sort_order', 'INT NOT NULL DEFAULT 0');
DROP PROCEDURE IF EXISTS add_column_if_missing;

CREATE TABLE IF NOT EXISTS knowledge_category (
    category_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_knowledge_category_status (status),
    INDEX idx_knowledge_category_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS model_config (
    config_id VARCHAR(64) PRIMARY KEY,
    model_type VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    base_url VARCHAR(512) NOT NULL DEFAULT '',
    model_name VARCHAR(255) NOT NULL,
    api_key_ciphertext TEXT NOT NULL,
    options JSON NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    updated_by VARCHAR(64) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS system_setting (
    setting_key VARCHAR(128) PRIMARY KEY,
    value JSON NOT NULL,
    description VARCHAR(512) NOT NULL DEFAULT '',
    updated_by VARCHAR(64) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO iam_permission (permission_code, name, permission_type, parent_code) VALUES
('faq:read', '查看 FAQ', 'api', 'faq:manage'),
('gap:read', '查看知识缺口', 'api', 'gap:manage'),
('model:manage', '模型配置管理', 'api', ''),
('system:manage', '系统参数管理', 'api', ''),
('audit:export', '审计导出', 'button', 'audit:read'),
('knowledge:download', '知识原文件下载', 'button', 'knowledge:read');

INSERT IGNORE INTO iam_role_permission (role_id, permission_code) VALUES
('role-system-admin', 'model:manage'),
('role-system-admin', 'system:manage'),
('role-system-admin', 'audit:export'),
('role-knowledge-admin', 'faq:read'),
('role-knowledge-admin', 'gap:read'),
('role-knowledge-admin', 'knowledge:download');

INSERT IGNORE INTO knowledge_category (category_id, name, description, status, sort_order) VALUES
('finance', '财务制度', '财务、报销、预算相关制度', 'active', 10),
('hr', '人力资源', '人事、薪酬、考勤和员工制度', 'active', 20),
('product', '产品与研发', '产品、研发和项目规范', 'active', 30),
('operation', '运营管理', '运营流程与服务规范', 'active', 40),
('general', '通用制度', '公司通用规章制度', 'active', 50);
