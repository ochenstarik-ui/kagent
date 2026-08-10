CREATE TABLE IF NOT EXISTS totp_challenges (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_totp_challenges_account ON totp_challenges(account_id);

ALTER TABLE accounts
ADD COLUMN IF NOT EXISTS totp_last_step BIGINT;
