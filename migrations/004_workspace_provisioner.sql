-- KAgent v0.10: persistent workspace provisioner and worker leases.

ALTER TABLE agent_workspaces
    ADD COLUMN IF NOT EXISTS task_contract JSONB,
    ADD COLUMN IF NOT EXISTS contract_digest TEXT;

UPDATE agent_workspaces
SET status = 'failed', updated_at = now()
WHERE task_contract IS NULL
  AND status NOT IN ('completed','failed','cancelled');

UPDATE agent_workspaces
SET task_contract = jsonb_build_object(
      'schemaVersion', '1',
      'projectId', project_id,
      'taskId', task_id,
      'objective', 'Legacy workspace migrated to v0.10',
      'contextRefs', '[]'::jsonb,
      'allowedPaths', jsonb_build_array('**'),
      'requiredChecks', '[]'::jsonb,
      'limits', jsonb_build_object(
        'maxRuntimeMinutes', max_runtime_minutes,
        'maxChangedFiles', max_changed_files,
        'maxConcurrentAgents', max_concurrent_agents,
        'networkAccess', network_access
      ),
      'issuedAt', created_at
    ),
    contract_digest = encode(
      digest(
        convert_to(
          jsonb_build_object(
            'schemaVersion', '1',
            'projectId', project_id,
            'taskId', task_id,
            'objective', 'Legacy workspace migrated to v0.10',
            'contextRefs', '[]'::jsonb,
            'allowedPaths', jsonb_build_array('**'),
            'requiredChecks', '[]'::jsonb,
            'limits', jsonb_build_object(
              'maxRuntimeMinutes', max_runtime_minutes,
              'maxChangedFiles', max_changed_files,
              'maxConcurrentAgents', max_concurrent_agents,
              'networkAccess', network_access
            ),
            'issuedAt', created_at
          )::text,
          'UTF8'
        ),
        'sha256'
      ),
      'hex'
    )
WHERE task_contract IS NULL OR contract_digest IS NULL;

ALTER TABLE agent_workspaces
    ALTER COLUMN task_contract SET NOT NULL,
    ALTER COLUMN contract_digest SET NOT NULL;

ALTER TABLE agent_workspaces
    ADD CONSTRAINT agent_workspaces_contract_digest_check
    CHECK (contract_digest ~ '^[0-9a-f]{64}$');

CREATE TABLE IF NOT EXISTS workspace_leases (
    workspace_id TEXT PRIMARY KEY REFERENCES agent_workspaces(id) ON DELETE CASCADE,
    worker_id    TEXT NOT NULL CHECK (worker_id ~ '^[a-zA-Z0-9._:-]{1,128}$'),
    token_hash   TEXT NOT NULL CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    generation   INTEGER NOT NULL DEFAULT 1 CHECK (generation > 0),
    acquired_at  TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    released_at  TIMESTAMPTZ,
    CHECK (expires_at >= heartbeat_at)
);

CREATE INDEX IF NOT EXISTS idx_workspace_leases_expiry
    ON workspace_leases(expires_at)
    WHERE released_at IS NULL;

CREATE TABLE IF NOT EXISTS workspace_provisioning (
    workspace_id  TEXT PRIMARY KEY REFERENCES agent_workspaces(id) ON DELETE CASCADE,
    worker_id     TEXT NOT NULL,
    checkout_ref  TEXT NOT NULL UNIQUE CHECK (checkout_ref ~ '^checkout:[a-zA-Z0-9_-]{1,128}$'),
    head_sha      TEXT CHECK (head_sha IS NULL OR head_sha ~ '^[0-9a-f]{40,64}$'),
    status        TEXT NOT NULL CHECK (status IN ('ready','failed','cleaned')),
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status != 'ready' OR head_sha IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_workspace_provisioning_worker
    ON workspace_provisioning(worker_id, status);
