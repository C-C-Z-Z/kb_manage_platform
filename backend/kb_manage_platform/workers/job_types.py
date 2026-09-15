"""集中定义后台任务类型，避免调度器和处理器使用字符串漂移。"""

INGEST_DOCUMENT_JOB_TYPE = "ingest_document"
FAQ_MINING_JOB_TYPE = "faq.mining"
GAP_DETECTION_JOB_TYPE = "gap.detection"