-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    feishu_open_id  VARCHAR(128) UNIQUE NOT NULL,
    feishu_union_id VARCHAR(128) UNIQUE NOT NULL,
    name        VARCHAR(64) NOT NULL,
    avatar_url  VARCHAR(512),
    role        VARCHAR(32) NOT NULL DEFAULT 'employee',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Contents table (with pgvector embedding column)
CREATE TABLE IF NOT EXISTS contents (
    id           SERIAL PRIMARY KEY,
    title        VARCHAR(256) NOT NULL,
    description  TEXT,
    tags         JSONB NOT NULL DEFAULT '[]',
    content_type VARCHAR(32) NOT NULL,
    status       VARCHAR(32) NOT NULL DEFAULT 'pending',
    file_key     VARCHAR(512) NOT NULL,
    file_url     VARCHAR(1024),
    file_size    INTEGER,
    ai_summary   TEXT,
    ai_keywords  JSONB NOT NULL DEFAULT '[]',
    embedding    vector(1536),
    uploaded_by  INTEGER NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS contents_status_idx ON contents (status);
CREATE INDEX IF NOT EXISTS contents_uploaded_by_idx ON contents (uploaded_by);
-- ivfflat index for approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS contents_embedding_idx ON contents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id              SERIAL PRIMARY KEY,
    content_id      INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    auditor_id      INTEGER NOT NULL REFERENCES users(id),
    audit_status    VARCHAR(32) NOT NULL,
    audit_comments  TEXT,
    audit_time      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_logs_content_id_idx ON audit_logs (content_id);
