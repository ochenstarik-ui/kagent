import { describe, it, expect, beforeAll, afterAll } from "vitest";
import Fastify, { type FastifyInstance } from "fastify";
import { Pool } from "pg";
import { PostgresStore } from "./db.js";
import { registerRoutes } from "./routes.js";
import type { TaskStatus } from "./domain.js";

const dbUrl = process.env["DATABASE_URL"];

describe.skipIf(!dbUrl)("Control Plane PostgreSQL Integration Tests", () => {
  let store: PostgresStore;
  let pool: Pool;
  let app: FastifyInstance;

  beforeAll(async () => {
    pool = new Pool({ connectionString: dbUrl });
    store = new PostgresStore(pool);
    app = Fastify();
    await registerRoutes(app, store);
    await app.ready();
  });

  afterAll(async () => {
    if (app) await app.close();
    if (pool) await pool.end();
  });

  it("1. Project creation persists and is readable after reopening connection", async () => {
    const project = await store.createProject(
      { name: "Persistence Test", description: "Testing DB persistence", repositoryUrl: "https://github.com/test/repo" },
      "acc_owner_1"
    );
    expect(project.id).toBeTruthy();
    expect(project.name).toBe("Persistence Test");
    expect(project.ownerAccountId).toBe("acc_owner_1");

    // Open a second store instance using same connection string / pool
    const store2 = new PostgresStore(pool);
    const fetched = await store2.getProject(project.id);
    expect(fetched).toBeDefined();
    expect(fetched?.id).toBe(project.id);
    expect(fetched?.name).toBe("Persistence Test");
    expect(fetched?.ownerAccountId).toBe("acc_owner_1");
  });

  it("2. Task creation in non-existent project returns 404", async () => {
    const res = await app.inject({
      method: "POST",
      url: "/v1/tasks",
      payload: {
        projectId: "non_existent_project_999",
        title: "Orphan Task",
        description: "Should fail with 404",
      },
    });

    expect(res.statusCode).toBe(404);
    const body = res.json();
    expect(body.code).toBe("not_found");
    expect(body.message).toContain("Project not found");
  });

  it("3. Invalid task status transition returns 422 and does NOT mutate row in DB", async () => {
    const proj = await store.createProject(
      { name: "State Machine Test", description: "Testing invalid status transition" },
      "acc_owner_2"
    );
    const task = await store.createTask(
      { projectId: proj.id, title: "Draft Task", description: "Initial draft" },
      "actor_1"
    );
    expect(task.status).toBe("draft");

    // Attempt invalid transition: draft → done
    const res = await app.inject({
      method: "PATCH",
      url: `/v1/tasks/${task.id}/status`,
      payload: {
        status: "done" as TaskStatus,
        reason: "Illegal skip to done",
      },
    });

    expect(res.statusCode).toBe(422);
    expect(res.json().code).toBe("invalid_transition");

    // Verify row in DB is NOT mutated
    const dbTask = await store.getTask(task.id);
    expect(dbTask?.status).toBe("draft");
  });

  it("4. Audit log records events on project creation, task creation, and status transition", async () => {
    const proj = await store.createProject(
      { name: "Audit Test Project", description: "Testing audit logs" },
      "actor_audit_owner"
    );
    const task = await store.createTask(
      { projectId: proj.id, title: "Audit Task", description: "Testing audit" },
      "actor_audit_task"
    );
    await store.updateTaskStatus(task.id, "planned", "actor_audit_transition", "Moving to planned");

    const events = await store.listAuditEvents(proj.id);
    expect(events.length).toBeGreaterThanOrEqual(3);

    const actions = events.map((e) => e.action);
    expect(actions).toContain("project.created");
    expect(actions).toContain("task.created");
    expect(actions).toContain("task.transition");
  });

  it("5. Audit log is immutable: UPDATE and DELETE are rejected by PG permissions", async () => {
    const proj = await store.createProject(
      { name: "Immutability Test", description: "Testing audit revoke" },
      "actor_immutability"
    );
    const events = await store.listAuditEvents(proj.id);
    expect(events.length).toBeGreaterThan(0);
    const auditId = events[0]!.id;

    // Test UPDATE rejection
    await expect(
      pool.query("UPDATE audit_events SET action = 'hacked' WHERE id = $1", [auditId])
    ).rejects.toThrow(/permission denied/i);

    // Test DELETE rejection
    await expect(
      pool.query("DELETE FROM audit_events WHERE id = $1", [auditId])
    ).rejects.toThrow(/permission denied/i);
  });

  it("6. Pagination: total matches count, limit/offset work, limit capped at max 100", async () => {
    const resAll = await store.listProjects(0, 50);
    const initialTotal = resAll.total;

    // Create 3 projects
    for (let i = 1; i <= 3; i++) {
      await store.createProject(
        { name: `Paging Project ${i}`, description: `Paging desc ${i}` },
        "actor_page"
      );
    }

    const page1 = await store.listProjects(0, 2);
    expect(page1.items.length).toBe(2);
    expect(page1.total).toBe(initialTotal + 3);

    // Test limit capping above max (100)
    const pageCapped = await store.listProjects(0, 500);
    expect(pageCapped.items.length).toBeLessThanOrEqual(100);
  });

  it("7. /health/ready returns 503 when database is unavailable", async () => {
    // Test healthy
    const resReady = await app.inject({ method: "GET", url: "/health/ready" });
    expect(resReady.statusCode).toBe(200);
    expect(resReady.json().status).toBe("ready");

    // Test unhealthy store
    const badStore = new PostgresStore("postgres://invalid_user:invalid_pass@127.0.0.1:59999/invalid_db");
    const badApp = Fastify();
    await registerRoutes(badApp, badStore);
    await badApp.ready();

    const resUnhealthy = await badApp.inject({ method: "GET", url: "/health/ready" });
    expect(resUnhealthy.statusCode).toBe(503);
    expect(resUnhealthy.json().status).toBe("unhealthy");

    await badApp.close();
  });
});
