/** PostgreSQL adapter for the persistent Control Plane domain. */

import { nanoid } from "nanoid";
import { Pool } from "pg";
import {
  TASK_TRANSITIONS,
  type AuditEvent,
  type CreateProjectInput,
  type CreateTaskInput,
  type Project,
  type Task
} from "./domain.js";

type DbRow = Record<string, unknown>;

function iso(value: unknown): string {
  return value instanceof Date ? value.toISOString() : String(value);
}

function projectFromRow(row: DbRow): Project {
  return {
    id: String(row["id"]),
    name: String(row["name"]),
    description: String(row["description"]),
    status: row["status"] as Project["status"],
    ownerAccountId: String(row["owner_account_id"]),
    ...(row["repository_url"] ? { repositoryUrl: String(row["repository_url"]) } : {}),
    createdAt: iso(row["created_at"]),
    updatedAt: iso(row["updated_at"])
  };
}

function taskFromRow(row: DbRow): Task {
  return {
    id: String(row["id"]),
    projectId: String(row["project_id"]),
    title: String(row["title"]),
    description: String(row["description"]),
    status: row["status"] as Task["status"],
    ...(row["assigned_agent_id"] ? { assignedAgentId: String(row["assigned_agent_id"]) } : {}),
    ...(row["capability"] ? { capability: String(row["capability"]) } : {}),
    contextRefs: Array.isArray(row["context_refs"])
      ? row["context_refs"].map(String)
      : [],
    createdAt: iso(row["created_at"]),
    updatedAt: iso(row["updated_at"])
  };
}

function auditFromRow(row: DbRow): AuditEvent {
  return {
    id: String(row["id"]),
    projectId: String(row["project_id"]),
    ...(row["task_id"] ? { taskId: String(row["task_id"]) } : {}),
    actorId: String(row["actor_id"]),
    action: String(row["action"]),
    ...(row["previous_state"] ? { previousState: String(row["previous_state"]) } : {}),
    ...(row["new_state"] ? { newState: String(row["new_state"]) } : {}),
    metadata: (row["metadata"] ?? {}) as Record<string, unknown>,
    timestamp: iso(row["timestamp"])
  };
}

export class PostgresStore {
  private readonly pool: Pool;

  constructor(connectionString?: string) {
    this.pool = new Pool({
      connectionString:
        connectionString ??
        process.env["DATABASE_URL"] ??
        "postgres://kagent:change-me-locally@127.0.0.1:5432/kagent",
      max: 10,
      idleTimeoutMillis: 30000
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

  async listProjects(): Promise<Project[]> {
    const result = await this.pool.query(
      "SELECT * FROM projects WHERE status != 'deleted' ORDER BY created_at DESC"
    );
    return result.rows.map(row => projectFromRow(row as DbRow));
  }

  async getProject(id: string): Promise<Project | undefined> {
    const result = await this.pool.query("SELECT * FROM projects WHERE id = $1", [id]);
    return result.rows[0] ? projectFromRow(result.rows[0] as DbRow) : undefined;
  }

  async createProject(input: CreateProjectInput, ownerAccountId: string): Promise<Project> {
    const id = nanoid(12);
    const result = await this.pool.query(
      `INSERT INTO projects (id, name, description, owner_account_id, repository_url)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [id, input.name, input.description, ownerAccountId, input.repositoryUrl ?? null]
    );
    await this.audit(id, undefined, ownerAccountId, "project.created", { name: input.name });
    return projectFromRow(result.rows[0] as DbRow);
  }

  async updateProject(
    id: string,
    updates: Record<string, unknown>,
    actorId: string
  ): Promise<Project | undefined> {
    const allowed: Record<string, string> = {
      name: "name",
      description: "description",
      status: "status",
      repositoryUrl: "repository_url",
      repository_url: "repository_url"
    };
    const sets: string[] = [];
    const values: unknown[] = [id];
    for (const [key, value] of Object.entries(updates)) {
      const column = allowed[key];
      if (column) {
        values.push(value);
        sets.push(`${column} = $${values.length}`);
      }
    }
    if (!sets.length) return this.getProject(id);
    const result = await this.pool.query(
      `UPDATE projects SET ${sets.join(", ")}, updated_at = now()
       WHERE id = $1 RETURNING *`,
      values
    );
    if (!result.rows[0]) return undefined;
    await this.audit(id, undefined, actorId, "project.updated", { updates });
    return projectFromRow(result.rows[0] as DbRow);
  }

  async listTasks(projectId?: string): Promise<Task[]> {
    const result = projectId
      ? await this.pool.query(
          "SELECT * FROM tasks WHERE project_id = $1 ORDER BY created_at DESC",
          [projectId]
        )
      : await this.pool.query("SELECT * FROM tasks ORDER BY created_at DESC");
    return result.rows.map(row => taskFromRow(row as DbRow));
  }

  async getTask(id: string): Promise<Task | undefined> {
    const result = await this.pool.query("SELECT * FROM tasks WHERE id = $1", [id]);
    return result.rows[0] ? taskFromRow(result.rows[0] as DbRow) : undefined;
  }

  async createTask(input: CreateTaskInput, actorId: string): Promise<Task> {
    const id = nanoid(12);
    const result = await this.pool.query(
      `INSERT INTO tasks (id, project_id, title, description, capability, context_refs)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [
        id,
        input.projectId,
        input.title,
        input.description,
        input.capability ?? null,
        JSON.stringify(input.contextRefs ?? [])
      ]
    );
    await this.audit(input.projectId, id, actorId, "task.created", { title: input.title });
    return taskFromRow(result.rows[0] as DbRow);
  }

  async updateTaskStatus(
    id: string,
    newStatus: Task["status"],
    actorId: string,
    reason?: string
  ): Promise<{ task?: Task; error?: string }> {
    const task = await this.getTask(id);
    if (!task) return { error: "Task not found" };
    if (!TASK_TRANSITIONS[task.status].includes(newStatus)) {
      return { error: `Invalid transition: ${task.status} -> ${newStatus}` };
    }
    const result = await this.pool.query(
      "UPDATE tasks SET status = $1, updated_at = now() WHERE id = $2 RETURNING *",
      [newStatus, id]
    );
    await this.audit(task.projectId, id, actorId, "task.transition", {
      reason: reason ?? "status update",
      previousState: task.status,
      newState: newStatus
    });
    return { task: taskFromRow(result.rows[0] as DbRow) };
  }

  async listAuditEvents(projectId?: string, limit = 50): Promise<AuditEvent[]> {
    const result = projectId
      ? await this.pool.query(
          "SELECT * FROM audit_events WHERE project_id = $1 ORDER BY timestamp DESC LIMIT $2",
          [projectId, limit]
        )
      : await this.pool.query(
          "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT $1",
          [limit]
        );
    return result.rows.map(row => auditFromRow(row as DbRow));
  }

  private async audit(
    projectId: string,
    taskId: string | undefined,
    actorId: string,
    action: string,
    metadata: Record<string, unknown>
  ): Promise<void> {
    await this.pool.query(
      `INSERT INTO audit_events (id, project_id, task_id, actor_id, action, metadata)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [nanoid(16), projectId, taskId ?? null, actorId, action, JSON.stringify(metadata)]
    );
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

let singleton: PostgresStore | undefined;

export function getStore(): PostgresStore {
  singleton ??= new PostgresStore();
  return singleton;
}
