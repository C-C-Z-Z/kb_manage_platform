-- FAQ 挖掘、审核与知识缺口闭环表

CREATE TABLE IF NOT EXISTS knowledge_faq_candidate (
    candidate_id VARCHAR(64) PRIMARY KEY,
    representative_question VARCHAR(512) NOT NULL,
    normalized_hash VARCHAR(64) NOT NULL UNIQUE,
    standard_answer TEXT NOT NULL,
    frequency INT NOT NULL DEFAULT 0,
    distinct_users INT NOT NULL DEFAULT 0,
    permission_signature VARCHAR(128) NOT NULL DEFAULT 'mixed',
    status VARCHAR(32) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0,
    reviewed_by VARCHAR(64) NOT NULL DEFAULT '',
    reject_reason TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_faq_candidate_status (status),
    INDEX idx_faq_candidate_frequency (frequency)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_faq_candidate_source (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    candidate_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_faq_candidate_source (candidate_id, request_id),
    INDEX idx_faq_candidate_source_candidate (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_gap (
    gap_id VARCHAR(64) PRIMARY KEY,
    representative_question VARCHAR(512) NOT NULL,
    normalized_hash VARCHAR(64) NOT NULL UNIQUE,
    gap_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    frequency INT NOT NULL DEFAULT 0,
    department_ids JSON NOT NULL,
    max_similarity FLOAT NOT NULL DEFAULT 0,
    suggested_category VARCHAR(64) NOT NULL DEFAULT '',
    reason TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_knowledge_gap_type (gap_type),
    INDEX idx_knowledge_gap_status (status),
    INDEX idx_knowledge_gap_frequency (frequency)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_gap_source (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    gap_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    UNIQUE KEY uq_gap_source (gap_id, request_id),
    INDEX idx_gap_source_gap (gap_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_supplement_draft (
    draft_id VARCHAR(64) PRIMARY KEY,
    gap_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    category_id VARCHAR(64) NOT NULL,
    knowledge_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_supplement_gap (gap_id),
    INDEX idx_supplement_knowledge (knowledge_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;