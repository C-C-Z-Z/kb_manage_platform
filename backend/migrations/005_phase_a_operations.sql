-- 阶段 A：任务进度、细粒度权限和索引（可重复执行）

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

CALL add_column_if_missing('background_job', 'progress', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_missing('background_job', 'stage', 'VARCHAR(32) NULL');
UPDATE background_job SET stage = 'queued' WHERE stage IS NULL OR stage = '';
ALTER TABLE background_job MODIFY COLUMN stage VARCHAR(32) NOT NULL DEFAULT 'queued';
DROP PROCEDURE IF EXISTS add_column_if_missing;

DROP PROCEDURE IF EXISTS add_index_if_missing;
DELIMITER //
CREATE PROCEDURE add_index_if_missing(
    IN p_table_name VARCHAR(64),
    IN p_index_name VARCHAR(64),
    IN p_columns TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND index_name = p_index_name
    ) THEN
        SET @ddl = CONCAT(
            'CREATE INDEX `', p_index_name, '` ON `', p_table_name, '` (', p_columns, ')'
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//
DELIMITER ;

CALL add_index_if_missing('iam_user_role', 'idx_iam_user_role_role', '`role_id`');
CALL add_index_if_missing('knowledge_faq_candidate_source', 'idx_faq_candidate_source_request', '`request_id`');
CALL add_index_if_missing('knowledge_gap_source', 'idx_gap_source_request', '`request_id`');
CALL add_index_if_missing('iam_role_permission', 'idx_role_permission_code', '`permission_code`');
DROP PROCEDURE IF EXISTS add_index_if_missing;

INSERT IGNORE INTO iam_permission (permission_code, name, permission_type, parent_code) VALUES
('knowledge:read', '查看知识', 'api', ''),
('knowledge:create', '创建知识', 'button', 'knowledge:read'),
('knowledge:update', '维护知识', 'button', 'knowledge:read'),
('knowledge:publish', '发布知识', 'button', 'knowledge:read'),
('knowledge:disable', '停用或归档知识', 'button', 'knowledge:read'),
('knowledge:permission:manage', '配置知识权限', 'button', 'knowledge:read'),
('import:create', '导入文档', 'button', 'knowledge:read'),
('import:read', '查看导入任务', 'api', 'knowledge:read'),
('qa:session:read', '查看问答历史', 'api', 'qa:use');

INSERT IGNORE INTO iam_role_permission (role_id, permission_code) VALUES
('role-system-admin', 'knowledge:read'),
('role-system-admin', 'dashboard:read'),
('role-knowledge-admin', 'knowledge:read'),
('role-knowledge-admin', 'knowledge:create'),
('role-knowledge-admin', 'knowledge:update'),
('role-knowledge-admin', 'knowledge:publish'),
('role-knowledge-admin', 'knowledge:disable'),
('role-knowledge-admin', 'knowledge:permission:manage'),
('role-knowledge-admin', 'import:create'),
('role-knowledge-admin', 'import:read'),
('role-knowledge-admin', 'qa:session:read'),
('role-user', 'qa:session:read');

