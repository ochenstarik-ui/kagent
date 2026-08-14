CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations (filename)
VALUES ('000_schema_migrations.sql')
ON CONFLICT (filename) DO NOTHING;
