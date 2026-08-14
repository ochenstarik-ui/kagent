-- v0.10 Account Pool: provider account management
--
-- Adds pool assignment, state machine, and scheduling columns to the
-- existing accounts table.  Accounts represent AI-provider credentials
-- (opencode-go, nvidia, codex, …) that can be assigned to logical roles
-- (orchestrator | subagents) and cycle through states:
--
--   available  → rented      (acquire)
--   rented     → available   (release, success)
--   rented     → throttled   (release, 429 / RateLimit)
--   throttled  → available   (scheduled reset or manual)
--   rented     → failed      (release, auth error)
--   any        → disabled    (manual operator action)
--   disabled   → available   (manual operator re-enable)

ALTER TABLE accounts
  ADD COLUMN IF NOT EXISTS provider_pool   TEXT NOT NULL DEFAULT 'default',
  ADD COLUMN IF NOT EXISTS pool_state      TEXT NOT NULL DEFAULT 'available'
    CHECK (pool_state IN ('available', 'rented', 'throttled', 'failed', 'disabled')),
  ADD COLUMN IF NOT EXISTS throttled_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_used       TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_accounts_pool_state
  ON accounts (provider_pool, pool_state, last_used ASC NULLS FIRST);
