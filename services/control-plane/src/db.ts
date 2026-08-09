/** PostgreSQL adapter for Control Plane store. */

import { Pool } from "pg";
import { nanoid } from "nanoid";
import {
  type Project, type Task, type AuditEvent,
  type CreateProjectInput, type CreateTaskInput,
  TASK_TRANSITIONS,
} from "./domain.js";

// Helper functions to map DB snake_case columns to Domain camelCase models

function mapProject(row: any): Project {
  return {
    id: row.id,
    name: row.name,
    description: row.description ?? "",
    status: row.status,
    ownerAccountId: row.owner_account_id,
    repositoryUrl: row.repository_url ?? undefined,
    createdAt: row.created_at ? new Date(row.created_at).toISOString() : new Date().toISOString(),
    updatedAt: row.updated_at ? new Date(row.updated_at).toISOString() : new Date().toISOString(),
  };
}

function mapTask(row: any): Task {
  let contextRefs: string[] = [];
  if (typeof row.context_refs === "string") {
    try {
      contextRefs = JSON.parse(row.context_refs);
    } catch {
      contextRefs = [];
    }
  } else if (Array.isArray(row.context_refs)) {
    contextRefs = row.context_refs;
  }
  return {
    id: row.id,
    projectId: row.project_id,
    title: row.title,
    description: row.description ?? "",
    status: row.status,
    assignedAgentId: row.assigned_agent_id ?? undefined,
    capability: row.capability ?? undefined,
    contextRefs,
    createdAt: row.created_at ? new Date(row.created_at).toISOString() : new Date().toISOString(),
    updatedAt: row.updated_at ? new Date(row.updated_at).toISOString() : new Date().toISOString(),
  };
}

function mapAuditEvent(row: any): AuditEvent {
  let metadata: Record<string, unknown> = {};
  if (typeof row.metadata === "string") {
    try {
      metadata = JSON.parse(row.metadata);
    } catch {
      metadata = {};
    }
  } else if (row.metadata && typeof row.metadata === "object") {
    metadata = row.metadata;
  }
  return {
    id: row.id,
    projectId: row.project_id,
    taskId: row.task_id ?? undefined,
    actorId: row.actor_id,
    action: row.action,
    previousState: row.previous_state ?? undefined,
    newState: row.new_state ?? undefined,
    metadata,
    timestamp: row.timestamp ? new Date(row.timestamp).toISOString() : new Date().toISOString(),
  };
}

export class PostgresStore {
  private pool: Pool;

  constructor(connectionString?: string | Pool) {
    if (connectionString && typeof connectionString !== "string") {
      this.pool = connectionString;
    } else {
      this.pool = new Pool({
        connectionString: (connectionString as string) ?? process.env["DATABASE_URL"] ?? "postgres://kagent:change-me-locally@127.0.0.1:5432/kagent",
        max: 10,
        idleTimeoutMillis: 30000,
      });
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.pool.query("SELECT 1");
      return true;
    } catch {
      return false;
    }
  }

  async countProjects(): Promise<number> {
    const count = await this.pool.query("SELECT COUNT(*) FROM projects WHERE status != 'deleted'");
    return parseInt(count.rows[0].count, 10);
  }

  async countTasks(projectId?: string): Promise<number> {
    if (projectId) {
      const count = await this.pool.query("SELECT COUNT(*) FROM tasks WHERE project_id = $1", [projectId]);
      return parseInt(count.rows[0].count, 10);
    }
    const count = await this.pool.query("SELECT COUNT(*) FROM tasks");
    return parseInt(count.rows[0].count, 10);
  }

  // ── Projects ─────────────────────────────────

  async listProjects(offset = 0, limit = 50): Promise<{ items: Project[]; total: number }> {
    const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 100);
    const safeOffset = Math.max(Number(offset) || 0, 0);

    const count = await this.pool.query("SELECT COUNT(*) FROM projects WHERE status != 'deleted'");
    const result = await this.pool.query(
      "SELECT * FROM projects WHERE status != 'deleted' ORDER BY created_at DESC OFFSET $1 LIMIT $2",
      [safeOffset, safeLimit]
    );
    return {
      items: result.rows.map(mapProject),
      total: parseInt(count.rows[0].count, 10),
    };
  }

  async getProject(id: string): Promise<Project | undefined> {
    const result = await this.pool.query("SELECT * FROM projects WHERE id = $1", [id]);
    return result.rows[0] ? mapProject(result.rows[0]) : undefined;
  }

  async createProject(input: CreateProjectInput, ownerAccountId: string): Promise<Project> {
    const id = nanoid(12);
    const result = await this.pool.query(
      `INSERT INTO projects (id, name, description, owner_account_id, repository_url)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [id, input.name, input.description, ownerAccountId, input.repositoryUrl ?? null]
    );
    await this._audit(id, undefined, ownerAccountId, "project.created", { name: input.name });
    return mapProject(result.rows[0]);
  }

  async updateProject(id: string, updates: Record<string, unknown>, actorId: string): Promise<Project | undefined> {
    const sets: string[] = [];
    const values: unknown[] = [id];
    let idx = 2;

    const columnMap: Record<string, string> = {
      name: "name",
      description: "description",
      status: "status",
      repositoryUrl: "repository_url",
      repository_url: "repository_url",
    };

    for (const [key, val] of Object.entries(updates)) {
      const col = columnMap[key];
      if (col) {
        sets.push(`${col} = $${idx++}`);
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
      return mapProject(result.rows[0]);
    }
    return undefined;
  }

  // ── Tasks ────────────────────────────────────

  async listTasks(projectId?: string, offset = 0, limit = 50): Promise<{ items: Task[]; total: number }> {
    const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 100);
    const safeOffset = Math.max(Number(offset) || 0, 0);

    if (projectId) {
      const count = await this.pool.query("SELECT COUNT(*) FROM tasks WHERE project_id = $1", [projectId]);
      const result = await this.pool.query(
        "SELECT * FROM tasks WHERE project_id = $1 ORDER BY created_at DESC OFFSET $2 LIMIT $3",
        [projectId, safeOffset, safeLimit]
      );
      return {
        items: result.rows.map(mapTask),
        total: parseInt(count.rows[0].count, 10),
      };
    }
    const count = await this.pool.query("SELECT COUNT(*) FROM tasks");
    const result = await this.pool.query(
      "SELECT * FROM tasks ORDER BY created_at DESC OFFSET $1 LIMIT $2",
      [safeOffset, safeLimit]
    );
    return {
      items: result.rows.map(mapTask),
      total: parseInt(count.rows[0].count, 10),
    };
  }

  async getTask(id: string): Promise<Task | undefined> {
    const result = await this.pool.query("SELECT * FROM tasks WHERE id = $1", [id]);
    return result.rows[0] ? mapTask(result.rows[0]) : undefined;
  }

  async createTask(input: CreateTaskInput, actorId: string): Promise<Task> {
    const id = nanoid(12);
    const result = await this.pool.query(
      `INSERT INTO tasks (id, project_id, title, description, capability, context_refs)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [id, input.projectId, input.title, input.description, input.capability ?? null, JSON.stringify(input.contextRefs ?? [])]
    );
    await this._audit(input.projectId, id, actorId, "task.created", { title: input.title });
    return mapTask(result.rows[0]);
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

    return { task: mapTask(result.rows[0]) };
  }

  // ── Audit ────────────────────────────────────

  async listAuditEvents(projectId?: string, limit = 50): Promise<AuditEvent[]> {
    const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 100);
    if (projectId) {
      const result = await this.pool.query(
        "SELECT * FROM audit_events WHERE project_id = $1 ORDER BY timestamp DESC LIMIT $2",
        [projectId, safeLimit]
      );
      return result.rows.map(mapAuditEvent);
    }
    const result = await this.pool.query(
      "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT $1", [safeLimit]
    );
    return result.rows.map(mapAuditEvent);
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
