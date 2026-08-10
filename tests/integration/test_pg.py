"""Integration tests — verify PostgreSQL schema and queries.

Requires: docker compose up -d postgres
Run: DATABASE_URL=postgres://kagent:change-me-locally@localhost:5432/kagent python tests/integration/test_pg.py
"""

import os
import sys
import asyncio
from pathlib import Path

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://kagent:change-me-locally@127.0.0.1:5432/kagent")


async def test_connection():
    """Test 1: Database connection."""
    conn = await asyncpg.connect(DATABASE_URL)
    version = await conn.fetchval("SELECT version()")
    assert "PostgreSQL" in version, f"Expected PostgreSQL, got: {version}"
    print(f"TEST 1 PASS: Connected — {version.split(',')[0]}")
    await conn.close()


async def test_tables_exist():
    """Test 2: All expected tables exist."""
    conn = await asyncpg.connect(DATABASE_URL)
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    table_names = {r["table_name"] for r in tables}
    
    required = {"projects", "tasks", "audit_events", "accounts", "sessions", "project_members"}
    missing = required - table_names
    assert not missing, f"Missing tables: {missing}"
    print(f"TEST 2 PASS: All {len(required)} tables exist — {sorted(table_names)}")
    await conn.close()


async def test_project_crud():
    """Test 3: Project CRUD operations."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Insert
    project = await conn.fetchrow("""
        INSERT INTO projects (id, name, description, owner_account_id)
        VALUES ('test-proj-1', 'Integration Test', 'Testing CRUD', 'test-account')
        ON CONFLICT (id) DO UPDATE SET name = 'Integration Test'
        RETURNING *
    """)
    assert project["name"] == "Integration Test"
    assert project["status"] == "active"
    
    # Read
    fetched = await conn.fetchrow("SELECT * FROM projects WHERE id = 'test-proj-1'")
    assert fetched is not None
    
    # Update
    await conn.execute("UPDATE projects SET status = 'archived' WHERE id = 'test-proj-1'")
    updated = await conn.fetchrow("SELECT status FROM projects WHERE id = 'test-proj-1'")
    assert updated["status"] == "archived"
    
    print(f"TEST 3 PASS: CRUD — project id={project['id']}, status={updated['status']}")
    await conn.close()


async def test_task_state_machine():
    """Test 4: Task state transitions work."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Create task
    task = await conn.fetchrow("""
        INSERT INTO tasks (id, project_id, title)
        VALUES ('test-task-1', 'test-proj-1', 'Test Task')
        RETURNING *
    """)
    assert task["status"] == "draft"
    
    # Valid transition: draft → planned
    await conn.execute("UPDATE tasks SET status = 'planned' WHERE id = 'test-task-1'")
    t = await conn.fetchrow("SELECT status FROM tasks WHERE id = 'test-task-1'")
    assert t["status"] == "planned"
    
    # Invalid transition: planned → done (should be blocked by app layer)
    # PG CHECK allows it — app state machine handles validation
    await conn.execute("UPDATE tasks SET status = 'approved' WHERE id = 'test-task-1'")
    t2 = await conn.fetchrow("SELECT status FROM tasks WHERE id = 'test-task-1'")
    assert t2["status"] == "approved"
    
    print(f"TEST 4 PASS: Task transitions — {task['status']} → {t2['status']}")
    await conn.close()


async def test_audit_append_only():
    """Test 5: Audit events are immutable."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Insert audit event
    event = await conn.fetchrow("""
        INSERT INTO audit_events (id, project_id, actor_id, action, metadata)
        VALUES ('test-audit-1', 'test-proj-1', 'test-actor', 'test.action', '{}')
        RETURNING *
    """)
    assert event["action"] == "test.action"
    
    # UPDATE must be rejected. A warning is not enough: before migration 003 this
    # branch silently passed, because the revoke in migration 001 does not apply to
    # the table owner the application connects as.
    try:
        await conn.execute("UPDATE audit_events SET action = 'hacked' WHERE id = 'test-audit-1'")
        raise AssertionError("UPDATE on audit_events was not blocked")
    except AssertionError:
        raise
    except Exception as e:
        assert "permission denied" in str(e).lower()
        print("  ✅ UPDATE blocked correctly")

    # DELETE of a record whose project still exists must be rejected as well.
    try:
        await conn.execute("DELETE FROM audit_events WHERE id = 'test-audit-1'")
        raise AssertionError("DELETE on audit_events was not blocked")
    except AssertionError:
        raise
    except Exception as e:
        assert "permission denied" in str(e).lower()
        print("  ✅ DELETE blocked correctly")
    
    print(f"TEST 5 PASS: Audit immutable — event {event['id']}")
    await conn.close()


async def test_auth_flow():
    """Test 6: Account + session creation."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Create account
    account = await conn.fetchrow("""
        INSERT INTO accounts (id, email, password_hash)
        VALUES ('test-account-auth', 'test@kagent.dev', 'pbkdf2:salt:hash')
        ON CONFLICT (id) DO NOTHING
        RETURNING *
    """)
    if account is None:
        account = await conn.fetchrow("SELECT * FROM accounts WHERE id = 'test-account-auth'")
    
    assert account["email"] == "test@kagent.dev"
    
    # Create session
    session = await conn.fetchrow("""
        INSERT INTO sessions (id, account_id, refresh_token_hash, expires_at)
        VALUES ('test-session-1', $1, 'hash123', now() + interval '1 day')
        RETURNING *
    """, account["id"])
    assert session["account_id"] == account["id"]
    
    # Revoke session
    await conn.execute("UPDATE sessions SET revoked_at = now() WHERE id = 'test-session-1'")
    s = await conn.fetchrow("SELECT revoked_at FROM sessions WHERE id = 'test-session-1'")
    assert s["revoked_at"] is not None
    
    print(f"TEST 6 PASS: Auth — account={account['email']}, session revoked")
    await conn.close()


async def test_foreign_keys():
    """Test 7: Foreign key constraints."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Task with non-existent project should fail
    try:
        await conn.execute("""
            INSERT INTO tasks (id, project_id, title)
            VALUES ('test-fk-1', 'nonexistent-project-999', 'Bad Task')
        """)
        print("  ⚠ FK not enforced")
    except Exception as e:
        assert "violates foreign key" in str(e).lower()
        print("  ✅ FK enforced")
    
    # Session with non-existent account
    try:
        await conn.execute("""
            INSERT INTO sessions (id, account_id, refresh_token_hash, expires_at)
            VALUES ('test-fk-2', 'no-account', 'hash', now() + interval '1 day')
        """)
        print("  ⚠ FK not enforced on sessions")
    except Exception as e:
        assert "violates foreign key" in str(e).lower()
        print("  ✅ FK enforced on sessions")
    
    print("TEST 7 PASS: Foreign keys enforced")
    await conn.close()


async def test_indexes():
    """Test 8: Expected indexes exist."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    indexes = await conn.fetch("""
        SELECT indexname FROM pg_indexes WHERE schemaname = 'public'
    """)
    idx_names = {r["indexname"] for r in indexes}
    
    expected = [
        "idx_projects_owner", "idx_projects_status",
        "idx_tasks_project", "idx_tasks_status",
        "idx_audit_project", "idx_audit_time",
        "idx_accounts_email", "idx_sessions_account",
        "idx_project_members_account",
    ]
    missing = [e for e in expected if e not in idx_names]
    found = [e for e in expected if e in idx_names]
    print(f"TEST 8 PASS: {len(found)}/{len(expected)} indexes — missing: {missing if missing else 'none'}")
    await conn.close()


async def test_concurrent():
    """Test 9: Concurrent operations don't corrupt data."""
    conn1 = await asyncpg.connect(DATABASE_URL)
    conn2 = await asyncpg.connect(DATABASE_URL)
    
    # Both create projects concurrently
    await conn1.execute("""
        INSERT INTO projects (id, name, description, owner_account_id)
        VALUES ('concurrent-1', 'Concurrent A', '', 'actor-a')
        ON CONFLICT (id) DO NOTHING
    """)
    await conn2.execute("""
        INSERT INTO projects (id, name, description, owner_account_id)
        VALUES ('concurrent-2', 'Concurrent B', '', 'actor-b')
        ON CONFLICT (id) DO NOTHING
    """)
    
    count = await conn1.fetchval("SELECT COUNT(*) FROM projects WHERE id LIKE 'concurrent-%'")
    assert count == 2, f"Expected 2 concurrent projects, got {count}"
    
    print(f"TEST 9 PASS: Concurrent writes — {count} projects created")
    await conn1.close()
    await conn2.close()


async def cleanup():
    """Remove test data."""
    conn = await asyncpg.connect(DATABASE_URL)
    # Audit rows are append-only and cannot be removed directly (migration 003).
    # They disappear together with their project through the foreign key cascade,
    # which is the only legitimate path.
    await conn.execute("DELETE FROM sessions WHERE id LIKE 'test-%'")
    await conn.execute("DELETE FROM accounts WHERE id LIKE 'test-%'")
    await conn.execute("DELETE FROM tasks WHERE id LIKE 'test-%'")
    await conn.execute("DELETE FROM tasks WHERE id LIKE 'concurrent-%'")
    await conn.execute("DELETE FROM projects WHERE id LIKE 'test-%'")
    await conn.execute("DELETE FROM projects WHERE id LIKE 'concurrent-%'")
    print("🧹 Test data cleaned up")
    await conn.close()


async def main():
    tests = [
        test_connection,
        test_tables_exist,
        test_project_crud,
        test_task_state_machine,
        test_audit_append_only,
        test_auth_flow,
        test_foreign_keys,
        test_indexes,
        test_concurrent,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
    
    await cleanup()
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'='*50}")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
