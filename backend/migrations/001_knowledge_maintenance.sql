-- 知识维护与四维权限配置基础表

CREATE TABLE IF NOT EXISTS knowledge_unit (
    knowledge_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category_id VARCHAR(64) NOT NULL,
    tags JSON NOT NULL,
    status VARCHAR(32) NOT NULL,
    current_version_id VARCHAR(64) NULL,
    created_by VARCHAR(64) NOT NULL,
    updated_by VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_knowledge_status (status),
    INDEX idx_knowledge_category (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_version (
    version_id VARCHAR(64) PRIMARY KEY,
    knowledge_id VARCHAR(64) NOT NULL,
    version_no INT NOT NULL,
    source_object_key VARCHAR(512) NOT NULL,
    markdown_object_key VARCHAR(512) NOT NULL DEFAULT '',
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    error_message TEXT NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_version_knowledge (knowledge_id),
    INDEX idx_version_status (status),
    UNIQUE KEY uq_knowledge_version_no (knowledge_id, version_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    knowledge_id VARCHAR(64) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    subject_id VARCHAR(64) NOT NULL,
    include_descendants TINYINT(1) NOT NULL DEFAULT 0,
    permission_version INT NOT NULL DEFAULT 1,
    created_by VARCHAR(64) NOT NULL,
    updated_by VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_knowledge_permission (knowledge_id, scope, subject_id, include_descendants),
    INDEX idx_permission_knowledge (knowledge_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS background_job (
    job_id VARCHAR(64) PRIMARY KEY,
    job_type VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(32) NOT NULL,
    priority INT NOT NULL DEFAULT 0,
    run_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_by VARCHAR(64) NULL,
    locked_at DATETIME NULL,
    heartbeat_at DATETIME NULL,
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    idempotency_key VARCHAR(128) NOT NULL,
    last_error TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_job_idempotency (idempotency_key),
    INDEX idx_job_poll (status, run_at, priority),
    INDEX idx_job_locked (locked_by, heartbeat_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;