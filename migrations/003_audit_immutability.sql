-- v0.9: Audit log immutability
--
-- Migration 001 revokes UPDATE and DELETE on audit_events from PUBLIC. That is
-- insufficient: the application connects as the table owner, and ownership
-- privileges are not affected by a revoke from PUBLIC. The append-only guarantee
-- required by the specification and the threat model was therefore not enforced
-- for the only role that actually writes to the table.
--
-- Triggers enforce the guarantee for every role, owner included.
--
-- One exception is deliberate. Deleting a project cascades to its audit rows, and
-- blocking that would make projects undeletable. A cascade is distinguishable from
-- tampering: by the time the child row is removed, the parent project row is
-- already gone within the same statement. Removing an audit record while its
-- project still exists is tampering and stays blocked.

CREATE OR REPLACE FUNCTION audit_events_reject_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE'
       AND NOT EXISTS (SELECT 1 FROM projects WHERE id = OLD.project_id) THEN
        -- cascade from an explicit project deletion
        RETURN OLD;
    END IF;

    RAISE EXCEPTION
        'permission denied: audit_events is append-only (attempted %)', TG_OP
        USING ERRCODE = '42501';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;
CREATE TRIGGER audit_events_no_update
    BEFORE UPDATE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_reject_mutation();

DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events;
CREATE TRIGGER audit_events_no_delete
    BEFORE DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_reject_mutation();

-- TRUNCATE bypasses row-level triggers, so it is blocked separately and has no
-- cascade exception: there is no legitimate reason to empty the audit table.
DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events;
CREATE TRIGGER audit_events_no_truncate
    BEFORE TRUNCATE ON audit_events
    FOR EACH STATEMENT EXECUTE FUNCTION audit_events_reject_mutation();

INSERT INTO schema_migrations (filename) VALUES ('003_audit_immutability.sql')
ON CONFLICT (filename) DO NOTHING;
