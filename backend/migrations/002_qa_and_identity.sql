-- AI 鉴权问答所需 IAM、FAQ、会话和审计表

CREATE TABLE IF NOT EXISTS iam_department (
    department_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    parent_id VARCHAR(64) NULL,
    path VARCHAR(1024) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS iam_user (
    user_id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(128) NOT NULL UNIQUE,
    department_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    permission_version INT NOT NULL DEFAULT 1,
    INDEX idx_iam_user_department (department_id),
    INDEX idx_iam_user_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS iam_role (
    role_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS iam_user_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL,
    role_id VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_user_role (user_id, role_id),
    INDEX idx_user_role_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_faq (
    faq_id VARCHAR(64) PRIMARY KEY,
    standard_question VARCHAR(512) NOT NULL,
    normalized_hash VARCHAR(64) NOT NULL UNIQUE,
    answer_text TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    knowledge_id VARCHAR(64) NOT NULL DEFAULT '',
    version_id VARCHAR(64) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_faq_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_faq_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    faq_id VARCHAR(64) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    subject_id VARCHAR(64) NOT NULL,
    include_descendants TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_faq_permission (faq_id, scope, subject_id, include_descendants),
    INDEX idx_faq_permission_faq (faq_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS qa_session (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_qa_session_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS qa_message (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_qa_message_id (message_id),
    INDEX idx_qa_message_session (session_id, created_at),
    INDEX idx_qa_message_user (user_id),
    INDEX idx_qa_message_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS qa_citation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_id VARCHAR(64) NOT NULL,
    knowledge_id VARCHAR(64) NOT NULL,
    version_id VARCHAR(64) NOT NULL,
    chunk_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '',
    section_path VARCHAR(512) NOT NULL DEFAULT '',
    snippet TEXT NOT NULL,
    INDEX idx_qa_citation_message (message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS qa_audit (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_type VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_qa_audit_event (event_type),
    INDEX idx_qa_audit_request (request_id),
    INDEX idx_qa_audit_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;