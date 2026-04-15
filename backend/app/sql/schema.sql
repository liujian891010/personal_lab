PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS reports (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id        TEXT NOT NULL UNIQUE,
    file_path        TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    source_ref       TEXT NOT NULL,
    source_url       TEXT,
    source_domain    TEXT NOT NULL,
    source_type      TEXT NOT NULL DEFAULT 'url',
    skill_name       TEXT NOT NULL,
    generated_at     TEXT NOT NULL,
    author           TEXT,
    status           TEXT NOT NULL DEFAULT 'published',
    language         TEXT,
    summary          TEXT NOT NULL,
    content_hash     TEXT NOT NULL,
    body_size        INTEGER NOT NULL,
    storage_provider TEXT,
    storage_bucket   TEXT,
    object_key       TEXT,
    storage_status   TEXT NOT NULL DEFAULT 'legacy',
    folder_id_ref    TEXT REFERENCES report_folders(folder_id) ON DELETE SET NULL,
    deleted_at       TEXT,
    deleted_by       TEXT,
    purge_after      TEXT,
    storage_cleanup_status TEXT NOT NULL DEFAULT 'pending',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_generated_at ON reports(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_source_domain ON reports(source_domain);
CREATE INDEX IF NOT EXISTS idx_reports_skill_name ON reports(skill_name);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_folder_id_ref ON reports(folder_id_ref);
CREATE INDEX IF NOT EXISTS idx_reports_deleted_at ON reports(deleted_at);
CREATE INDEX IF NOT EXISTS idx_reports_purge_after ON reports(purge_after);
CREATE INDEX IF NOT EXISTS idx_reports_storage_cleanup_status ON reports(storage_cleanup_status);

CREATE TABLE IF NOT EXISTS report_tags (
    report_id_ref    TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    tag              TEXT NOT NULL,
    normalized_tag   TEXT NOT NULL,
    PRIMARY KEY (report_id_ref, normalized_tag)
);

CREATE INDEX IF NOT EXISTS idx_report_tags_normalized_tag ON report_tags(normalized_tag);

CREATE TABLE IF NOT EXISTS report_links (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id_ref    TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    url              TEXT NOT NULL,
    link_type        TEXT NOT NULL,
    anchor_text      TEXT,
    UNIQUE (report_id_ref, url, link_type)
);

CREATE INDEX IF NOT EXISTS idx_report_links_url ON report_links(url);

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    report_id UNINDEXED,
    title,
    summary,
    body,
    tags,
    source_domain,
    skill_name,
    tokenize = 'unicode61'
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type         TEXT NOT NULL,
    mode             TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    scanned_count    INTEGER NOT NULL DEFAULT 0,
    created_count    INTEGER NOT NULL DEFAULT 0,
    updated_count    INTEGER NOT NULL DEFAULT 0,
    deleted_count    INTEGER NOT NULL DEFAULT 0,
    failed_count     INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL,
    message          TEXT
);

CREATE TABLE IF NOT EXISTS report_delete_audit_logs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id          TEXT NOT NULL,
    action             TEXT NOT NULL,
    actor_user_id      TEXT,
    actor_workspace_id TEXT,
    detail             TEXT,
    created_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_report_delete_audit_logs_report_id
    ON report_delete_audit_logs(report_id, created_at DESC);

CREATE TABLE IF NOT EXISTS wiki_pages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id          TEXT NOT NULL UNIQUE,
    page_type        TEXT NOT NULL,
    file_path        TEXT NOT NULL UNIQUE,
    slug             TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'active',
    summary          TEXT,
    confidence       REAL,
    content_hash     TEXT NOT NULL,
    storage_provider TEXT,
    storage_bucket   TEXT,
    object_key       TEXT,
    storage_status   TEXT NOT NULL DEFAULT 'legacy',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wiki_pages_page_type ON wiki_pages(page_type);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_status ON wiki_pages(status);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_updated_at ON wiki_pages(updated_at DESC);

CREATE TABLE IF NOT EXISTS wiki_page_tags (
    page_id_ref      TEXT NOT NULL REFERENCES wiki_pages(page_id) ON DELETE CASCADE,
    tag              TEXT NOT NULL,
    normalized_tag   TEXT NOT NULL,
    PRIMARY KEY (page_id_ref, normalized_tag)
);

CREATE TABLE IF NOT EXISTS wiki_links (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id   TEXT NOT NULL,
    target_kind      TEXT NOT NULL,
    target_id        TEXT NOT NULL,
    link_type        TEXT NOT NULL,
    anchor_text      TEXT,
    is_resolved      INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_wiki_links_source ON wiki_links(source_page_id);
CREATE INDEX IF NOT EXISTS idx_wiki_links_target ON wiki_links(target_kind, target_id);

CREATE TABLE IF NOT EXISTS page_sources (
    page_id_ref      TEXT NOT NULL REFERENCES wiki_pages(page_id) ON DELETE CASCADE,
    report_id_ref    TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    evidence_role    TEXT NOT NULL,
    PRIMARY KEY (page_id_ref, report_id_ref, evidence_role)
);

CREATE TABLE IF NOT EXISTS knowledge_tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type        TEXT NOT NULL,
    target_kind      TEXT NOT NULL,
    target_id        TEXT,
    title            TEXT NOT NULL,
    description      TEXT,
    priority         TEXT NOT NULL DEFAULT 'medium',
    status           TEXT NOT NULL DEFAULT 'open',
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_conflicts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_key          TEXT NOT NULL,
    page_id_ref        TEXT,
    old_claim          TEXT NOT NULL,
    new_claim          TEXT NOT NULL,
    evidence_report_id TEXT,
    severity           TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'open',
    created_at         TEXT NOT NULL,
    resolved_at        TEXT
);

CREATE TABLE IF NOT EXISTS question_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text      TEXT NOT NULL,
    answer_summary     TEXT,
    wrote_back_page_id TEXT,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_run_sources (
    run_id             INTEGER NOT NULL REFERENCES question_runs(id) ON DELETE CASCADE,
    source_kind        TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    PRIMARY KEY (run_id, source_kind, source_id)
);

CREATE INDEX IF NOT EXISTS idx_qrun_sources_run ON question_run_sources(run_id);
CREATE INDEX IF NOT EXISTS idx_qrun_sources_source ON question_run_sources(source_kind, source_id);

CREATE VIRTUAL TABLE IF NOT EXISTS wiki_search_index USING fts5(
    page_id UNINDEXED,
    title,
    summary,
    body,
    tags,
    page_type,
    tokenize = 'unicode61'
);

CREATE TABLE IF NOT EXISTS report_folders (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id        TEXT NOT NULL UNIQUE,
    folder_name      TEXT NOT NULL,
    folder_slug      TEXT NOT NULL UNIQUE,
    description      TEXT,
    sort_order       INTEGER NOT NULL DEFAULT 0,
    report_count     INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    UNIQUE (folder_name COLLATE NOCASE)
);

CREATE INDEX IF NOT EXISTS idx_report_folders_slug ON report_folders(folder_slug);

CREATE TABLE IF NOT EXISTS upload_jobs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id          TEXT NOT NULL UNIQUE,
    original_filename  TEXT NOT NULL,
    stored_filename    TEXT NOT NULL,
    storage_path       TEXT NOT NULL UNIQUE,
    mime_type          TEXT,
    file_ext           TEXT NOT NULL,
    file_size_bytes    INTEGER NOT NULL,
    source_ref         TEXT NOT NULL UNIQUE,
    source_type        TEXT NOT NULL DEFAULT 'upload_file',
    title              TEXT,
    upload_status      TEXT NOT NULL,
    processing_stage   TEXT NOT NULL,
    report_id_ref      TEXT UNIQUE,
    auto_process       INTEGER NOT NULL DEFAULT 0,
    compile_mode       TEXT,
    auto_compile       INTEGER NOT NULL DEFAULT 0,
    triggered_by       TEXT NOT NULL DEFAULT 'user_upload',
    error_code         TEXT,
    error_message      TEXT,
    retry_count        INTEGER NOT NULL DEFAULT 0,
    content_hash       TEXT,
    storage_provider   TEXT,
    storage_bucket     TEXT,
    object_key         TEXT,
    storage_status     TEXT NOT NULL DEFAULT 'legacy',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    completed_at       TEXT,
    FOREIGN KEY (report_id_ref) REFERENCES reports(report_id) ON DELETE SET NULL,
    CHECK (source_type = 'upload_file'),
    CHECK (upload_status IN ('uploaded', 'queued', 'processing', 'completed', 'failed', 'needs_review')),
    CHECK (processing_stage IN ('received', 'stored', 'extracting', 'normalizing', 'summarizing', 'report_generating', 'syncing', 'compiling', 'done', 'error')),
    CHECK (compile_mode IS NULL OR compile_mode IN ('propose', 'apply_safe')),
    CHECK (auto_process IN (0, 1)),
    CHECK (auto_compile IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_upload_jobs_status ON upload_jobs(upload_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_stage ON upload_jobs(processing_stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_created_at ON upload_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_report_id_ref ON upload_jobs(report_id_ref);

CREATE TABLE IF NOT EXISTS upload_artifacts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id_ref      TEXT NOT NULL REFERENCES upload_jobs(upload_id) ON DELETE CASCADE,
    artifact_kind      TEXT NOT NULL,
    file_path          TEXT NOT NULL,
    content_hash       TEXT,
    byte_size          INTEGER,
    storage_provider   TEXT,
    storage_bucket     TEXT,
    object_key         TEXT,
    storage_status     TEXT NOT NULL DEFAULT 'legacy',
    created_at         TEXT NOT NULL,
    UNIQUE (upload_id_ref, artifact_kind, file_path)
);

CREATE INDEX IF NOT EXISTS idx_upload_artifacts_upload_id_ref
    ON upload_artifacts(upload_id_ref, artifact_kind);
