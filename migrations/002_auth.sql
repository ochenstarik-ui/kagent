-- v0.3 Auth: Accounts, Sessions, RBAC

-- Accounts
CREATE TABLE IF NOT EXISTS accounts (
    id              TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(8), 'hex'),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    totp_secret     TEXT,
    totp_enabled    BOOLEAN NOT NULL DEFAULT false,
    role            TEXT NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user', 'admin', 'system')),
    disabled_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_accounts_email ON accounts(email);

-- Sessions: one per login, revocable
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY DEFAULT encode(gen_random_bytes(12), 'hex'),
    account_id      TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,
    user_agent      TEXT,
    ip_address      TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_account ON sessions(account_id);
CREATE INDEX idx_sessions_refresh ON sessions(refresh_token_hash);

-- RBAC: which accounts have access to which projects
CREATE TABLE IF NOT EXISTS project_members (
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    account_id      TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'editor'
                    CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
    added_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, account_id)
);

CREATE INDEX idx_project_members_account ON project_members(account_id);

INSERT INTO schema_migrations (filename) VALUES ('002_auth.sql')
ON CONFLICT (filename) DO NOTHING;
