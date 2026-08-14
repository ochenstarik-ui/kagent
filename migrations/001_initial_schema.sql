-- KAgent v0.2: Initial schema
-- Projects, Tasks, Audit Events

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Projects: workspaces where agents operate
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(8), 'hex'),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'archived', 'deleted')),
    owner_account_id TEXT NOT NULL,
    repository_url   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_owner ON projects(owner_account_id);
CREATE INDEX idx_projects_status ON projects(status);

-- Tasks: units of work assigned to agents
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(8), 'hex'),
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','planned','approved','in_progress','review','done','cancelled')),
    assigned_agent_id TEXT,
    capability      TEXT,
    context_refs    JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status  ON tasks(status);
CREATE INDEX idx_tasks_agent   ON tasks(assigned_agent_id);

-- Audit: append-only event log
CREATE TABLE IF NOT EXISTS audit_events (
    id              TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(10), 'hex'),
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id         TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    actor_id        TEXT NOT NULL,
    action          TEXT NOT NULL,
    previous_state  TEXT,
    new_state       TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_project ON audit_events(project_id);
CREATE INDEX idx_audit_task    ON audit_events(task_id);
CREATE INDEX idx_audit_time    ON audit_events(timestamp DESC);

-- Immutable audit (no UPDATE/DELETE allowed via permissions)
REVOKE UPDATE, DELETE ON audit_events FROM PUBLIC;

INSERT INTO schema_migrations (filename) VALUES ('001_initial_schema.sql')
ON CONFLICT (filename) DO NOTHING;
