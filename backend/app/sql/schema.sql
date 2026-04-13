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
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_generated_at ON reports(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_source_domain ON reports(source_domain);
CREATE INDEX IF NOT EXISTS idx_reports_skill_name ON reports(skill_name);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

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
