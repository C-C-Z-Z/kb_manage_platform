export interface CurrentUser { user_id: string; username: string; department_id: string; role_ids: string[]; status: string; permission_codes: string[]; }
export interface TokenResponse { access_token: string; token_type: string; expires_in: number; user: CurrentUser; }
export interface PageResponse<T> { items: T[]; page: number; page_size: number; total: number; }
export interface KnowledgeUnit { knowledge_id: string; title: string; category_id: string; tags: string[]; status: string; current_version_id: string; created_by: string; updated_by: string; created_at: string; updated_at: string; }
export interface KnowledgeVersion { version_id: string; knowledge_id: string; version_no: number; source_object_key: string; markdown_object_key: string; filename: string; content_type: string; status: string; error_message: string; created_by: string; created_at: string; }
export interface PermissionGrant { scope: "global" | "department" | "role" | "user"; subject_id: string; include_descendants: boolean; }
export interface PermissionSet { knowledge_id: string; permission_version: number; grants: PermissionGrant[]; }
export interface Citation { chunk_id: string; knowledge_id: string; version_id: string; content: string; score: number; source: string; }
export interface ChatMessage { role: "user" | "assistant"; content: string; citations?: Citation[]; warnings?: string[]; requestId?: string; }
export interface SessionItem { session_id: string; title: string; created_at: string; updated_at: string; }
export interface ImportJob { job_id: string; job_type: string; status: string; progress: number; stage: string; attempts: number; max_attempts: number; last_error: string; created_at: string; updated_at: string; }
export interface Department { department_id: string; name: string; parent_id: string; path: string; status: string; sort_order: number; }
export interface UserAccount { user_id: string; username: string; department_id: string; status: string; permission_version: number; role_ids: string[]; }
export interface Role { role_id: string; name: string; status: string; permission_codes: string[]; }
export interface PermissionDefinition { permission_code: string; name: string; permission_type: string; parent_code: string; }
export interface DashboardTopItem { label: string; value: number; }
export interface DashboardTrendPoint { label: string; value: number; }
export interface DashboardOverview { range_days: number; pv: number; uv: number; knowledge_count: number; published_count: number; top_questions: DashboardTopItem[]; hot_knowledge: DashboardTopItem[]; token_total: number; avg_latency_ms: number; faq_hit_rate: number; coverage_rate: number; token_trend: DashboardTrendPoint[]; latency_trend: DashboardTrendPoint[]; }
export interface KnowledgeCategory { category_id: string; name: string; description: string; status: string; sort_order: number; }
export interface KnowledgeChunk { chunk_id: string; version_id: string; content: string; section_path: string; image_summary: string; }
export interface KnowledgePreview { knowledge_id: string; title: string; version_id: string; version_no: number; markdown: string; chunks: KnowledgeChunk[]; }
export interface FaqCandidate { candidate_id: string; question: string; answer: string; frequency: number; distinct_users: number; status: string; permission_signature: string; confidence: number; }
export interface PublishedFaq { faq_id: string; question: string; answer: string; status: string; knowledge_id: string; version_id: string; updated_at: string; }
export interface KnowledgeGap { gap_id: string; question: string; gap_type: string; status: string; frequency: number; departments: string[]; max_similarity: number; suggested_category: string; }
export interface AuditLog { event_id: number; event_type: string; request_id: string; user_id: string; payload: Record<string, unknown>; created_at: string; }
export interface ModelConfig { config_id: string; model_type: string; name: string; base_url: string; model_name: string; status: string; source: string; effective_source: string; runtime_applied: boolean; api_key_masked: string; local_model_path: string; options: Record<string, unknown>; }
export interface ModelTestResult { model_type: string; success: boolean; message: string; }
export interface SystemSetting { setting_key: string; value: unknown; description: string; updated_by: string; updated_at: string; }
