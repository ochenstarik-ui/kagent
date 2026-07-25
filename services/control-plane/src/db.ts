/** PostgreSQL adapter for Control Plane store. */

import { Pool, type PoolClient } from "pg";
import { nanoid } from "nanoid";
import {
  type Project, type Task, type AuditEvent,
  type CreateProjectInput, type CreateTaskInput,
  TASK_TRANSITIONS,
} from "./domain.js";

export class PostgresStore {
  private pool: Pool;

  constructor(connectionString?: string) {
    this.pool = new Pool({
      connectionString: connectionString ?? process.env["DATABASE_URL"] ?? "postgres://kagent:change-me-locally@127.0.0.1:5432/kagent",
      max: 10,
      idleTimeoutMillis: 30000,
    });
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.pool.query("SELECT 1");
      return true;
    } catch {
      return false;
    }
  }

  // ── Projects ─────────────────────────────────

  async listProjects(offset = 0, limit = 50): Promise<{ items: Project[]; total: number }> {
    const count = await this.pool.query("SELECT COUNT(*) FROM projects WHERE status != 'deleted'");
    const result = await this.pool.query(
      "SELECT * FROM projects WHERE status != 'deleted' ORDER BY created_at DESC OFFSET $1 LIMIT $2",
      [offset, limit]
    );
    return { items: result.rows, total: parseInt(count.rows[0].count, 10) };
  }

  async getProject(id: string): Promise<Project | undefined> {
    const result = await this.pool.query("SELECT * FROM projects WHERE id = $1", [id]);
    return result.rows[0] ?? undefined;
  }

  async createProject(input: CreateProjectInput, ownerAccountId: string): Promise<Project> {
    const id = nanoid(12);
    const result = await this.pool.query(
      `INSERT INTO projects (id, name, description, owner_account_id, repository_url)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [id, input.name, input.description, ownerAccountId, input.repositoryUrl ?? null]
    );
    await this._audit(id, undefined, ownerAccountId, "project.created", { name: input.name });
    return result.rows[0];
  }

  async updateProject(id: string, updates: Record<string, unknown>, actorId: string): Promise<Project | undefined> {
    const sets: string[] = [];
    const values: unknown[] = [id];
    let idx = 2;

    for (const [key, val] of Object.entries(updates)) {
      if (["name", "description", "status", "repository_url"].includes(key)) {
        sets.push(`${key} = $${idx++}`);
        values.push(val);
      }
    }
    if (sets.length === 0) return this.getProject(id);

    sets.push(`updated_at = now()`);
    const result = await this.pool.query(
      `UPDATE projects SET ${sets.join(", ")} WHERE id = $1 RETURNING *`,
      values
    );
    if (result.rows[0]) {
      await this._audit(id, undefined, actorId, "project.updated", { updates });
    }
    return result.rows[0] ?? undefined;
  }

  // ── Tasks ────────────────────────────────────

  async listTasks(projectId?: string): Promise<{ items: Task[]; total: number }> {
    if (projectId) {
      const count = await this.pool.query("SELECT COUNT(*) FROM tasks WHERE project_id = $1", [projectId]);
      const result = await this.pool.query(
        "SELECT * FROM tasks WHERE project_id = $1 ORDER BY created_at DESC", [projectId]
      );
      return { items: result.rows, total: parseInt(count.rows[0].count, 10) };
    }
    const count = await this.pool.query("SELECT COUNT(*) FROM tasks");
    const result = await this.pool.query("SELECT * FROM tasks ORDER BY created_at DESC");
    return { items: result.rows, total: parseInt(count.rows[0].count, 10) };
  }

  async getTask(id: string): Promise<Task | undefined> {
    const result = await this.pool.query("SELECT * FROM tasks WHERE id = $1", [id]);
    return result.rows[0] ?? undefined;
  }

  async createTask(input: CreateTaskInput, actorId: string): Promise<Task> {
    const id = nanoid(12);
    const result = await this.pool.query(
      `INSERT INTO tasks (id, project_id, title, description, capability, context_refs)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [id, input.projectId, input.title, input.description, input.capability ?? null, JSON.stringify(input.contextRefs ?? [])]
    );
    await this._audit(input.projectId, id, actorId, "task.created", { title: input.title });
    return result.rows[0];
  }

  async updateTaskStatus(id: string, newStatus: string, actorId: string, reason?: string): Promise<{ task?: Task; error?: string }> {
    const task = await this.getTask(id);
    if (!task) return { error: "Task not found" };

    const allowed = TASK_TRANSITIONS[task.status as keyof typeof TASK_TRANSITIONS];
    if (!allowed.includes(newStatus as never)) {
      return { error: `Invalid transition: ${task.status} → ${newStatus}` };
    }

    const previousState = task.status;
    const result = await this.pool.query(
      "UPDATE tasks SET status = $1, updated_at = now() WHERE id = $2 RETURNING *",
      [newStatus, id]
    );

    await this._audit(task.projectId, id, actorId, "task.transition", {
      reason: reason ?? "status update",
      previousState,
      newState: newStatus,
    });

    return { task: result.rows[0] };
  }

  // ── Audit ────────────────────────────────────

  async listAuditEvents(projectId?: string, limit = 50): Promise<AuditEvent[]> {
    if (projectId) {
      const result = await this.pool.query(
        "SELECT * FROM audit_events WHERE project_id = $1 ORDER BY timestamp DESC LIMIT $2",
        [projectId, limit]
      );
      return result.rows;
    }
    const result = await this.pool.query(
      "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT $1", [limit]
    );
    return result.rows;
  }

  private async _audit(projectId: string, taskId: string | undefined, actorId: string, action: string, meta: Record<string, unknown>) {
    await this.pool.query(
      `INSERT INTO audit_events (id, project_id, task_id, actor_id, action, metadata)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [nanoid(16), projectId, taskId ?? null, actorId, action, JSON.stringify(meta)]
    );
  }

  async close() {
    await this.pool.end();
  }
}

// Singleton
let _store: PostgresStore | null = null;

export function getStore(): PostgresStore {
  if (!_store) _store = new PostgresStore();
  return _store;
}
