-- KAgent v0.9: Agent workspace cockpit foundation
-- Workspace lifecycle, multiplexed session metadata and line-level diff review.

CREATE TABLE IF NOT EXISTS agent_workspaces (
    id                    TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(8), 'hex'),
    project_id            TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id               TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status                TEXT NOT NULL DEFAULT 'provisioning'
                          CHECK (status IN (
                            'provisioning','ready','running','paused',
                            'awaiting_approval','verifying','completed','failed','cancelled'
                          )),
    repository_url        TEXT NOT NULL,
    base_branch           TEXT NOT NULL DEFAULT 'main',
    branch_name           TEXT NOT NULL,
    workspace_ref         TEXT NOT NULL UNIQUE,
    max_runtime_minutes   INTEGER NOT NULL DEFAULT 120
                          CHECK (max_runtime_minutes BETWEEN 1 AND 1440),
    max_changed_files     INTEGER NOT NULL DEFAULT 30
                          CHECK (max_changed_files BETWEEN 1 AND 1000),
    max_concurrent_agents INTEGER NOT NULL DEFAULT 1
                          CHECK (max_concurrent_agents BETWEEN 1 AND 16),
    network_access        TEXT NOT NULL DEFAULT 'denied'
                          CHECK (network_access IN ('denied','allowlisted')),
    changed_files         INTEGER NOT NULL DEFAULT 0 CHECK (changed_files >= 0),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_workspaces_project ON agent_workspaces(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_workspaces_task ON agent_workspaces(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_workspaces_status ON agent_workspaces(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_workspaces_active_task
    ON agent_workspaces(task_id)
    WHERE status NOT IN ('completed','failed','cancelled');

CREATE TABLE IF NOT EXISTS workspace_sessions (
    id              TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(8), 'hex'),
    workspace_id    TEXT NOT NULL REFERENCES agent_workspaces(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('agent','terminal','browser')),
    title           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'starting'
                    CHECK (status IN ('starting','active','waiting','stopped','failed')),
    agent_harness   TEXT,
    worker_ref      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_sessions_workspace
    ON workspace_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_sessions_status
    ON workspace_sessions(status);

CREATE TABLE IF NOT EXISTS diff_review_comments (
    id              TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(8), 'hex'),
    workspace_id    TEXT NOT NULL REFERENCES agent_workspaces(id) ON DELETE CASCADE,
    path            TEXT NOT NULL CHECK (path !~ '(^/|(^|/)\.\.(/|$))'),
    line            INTEGER NOT NULL CHECK (line > 0),
    side            TEXT NOT NULL CHECK (side IN ('old','new')),
    body            TEXT NOT NULL CHECK (length(trim(body)) > 0),
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','resolved')),
    author_id       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_diff_review_comments_workspace
    ON diff_review_comments(workspace_id);
CREATE INDEX IF NOT EXISTS idx_diff_review_comments_open
    ON diff_review_comments(workspace_id, status);
