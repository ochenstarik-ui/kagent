/** In-memory store — will be replaced by PostgreSQL in v0.2+. */

import { nanoid } from "nanoid";
import {
  type Project, type Task, type AuditEvent,
  type CreateProjectInput, type CreateTaskInput,
  type ProjectStatus, type TaskStatus,
  TASK_TRANSITIONS,
} from "./domain.js";

export class Store {
  private projects = new Map<string, Project>();
  private tasks = new Map<string, Task>();
  private auditLog: AuditEvent[] = [];

  // ── Projects ─────────────────────────────────

  listProjects(): Project[] {
    return [...this.projects.values()];
  }

  getProject(id: string): Project | undefined {
    return this.projects.get(id);
  }

  createProject(input: CreateProjectInput, ownerAccountId: string): Project {
    const now = new Date().toISOString();
    const project: Project = {
      id: nanoid(12),
      name: input.name,
      description: input.description,
      status: "active" as ProjectStatus,
      ownerAccountId,
      repositoryUrl: input.repositoryUrl,
      createdAt: now,
      updatedAt: now,
    };
    this.projects.set(project.id, project);
    this.recordAudit({
      projectId: project.id,
      actorId: ownerAccountId,
      action: "project.created",
      metadata: { name: input.name },
    });
    return project;
  }

  updateProject(id: string, updates: Partial<Pick<Project, "name" | "description" | "status" | "repositoryUrl">>, actorId: string): Project | undefined {
    const p = this.projects.get(id);
    if (!p) return undefined;

    Object.assign(p, updates, { updatedAt: new Date().toISOString() });
    this.recordAudit({
      projectId: id,
      actorId,
      action: "project.updated",
      metadata: { updates },
    });
    return p;
  }

  // ── Tasks ────────────────────────────────────

  listTasks(projectId?: string): Task[] {
    const all = [...this.tasks.values()];
    return projectId ? all.filter(t => t.projectId === projectId) : all;
  }

  getTask(id: string): Task | undefined {
    return this.tasks.get(id);
  }

  createTask(input: CreateTaskInput, actorId: string): Task {
    const now = new Date().toISOString();
    const task: Task = {
      id: nanoid(12),
      projectId: input.projectId,
      title: input.title,
      description: input.description,
      status: "draft" as TaskStatus,
      capability: input.capability,
      contextRefs: input.contextRefs ?? [],
      createdAt: now,
      updatedAt: now,
    };
    this.tasks.set(task.id, task);
    this.recordAudit({
      projectId: input.projectId,
      taskId: task.id,
      actorId,
      action: "task.created",
      newState: "draft",
      metadata: { title: input.title },
    });
    return task;
  }

  updateTaskStatus(id: string, newStatus: TaskStatus, actorId: string, reason?: string): { task?: Task; error?: string } {
    const task = this.tasks.get(id);
    if (!task) return { error: "Task not found" };

    const allowed = TASK_TRANSITIONS[task.status];
    if (!allowed.includes(newStatus)) {
      return {
        error: `Invalid transition: ${task.status} → ${newStatus}. Allowed: ${allowed.join(", ")}`,
      };
    }

    const previousState = task.status;
    task.status = newStatus;
    task.updatedAt = new Date().toISOString();

    this.recordAudit({
      projectId: task.projectId,
      taskId: task.id,
      actorId,
      action: "task.transition",
      previousState,
      newState: newStatus,
      metadata: { reason: reason ?? "status update" },
    });

    return { task };
  }

  // ── Audit ────────────────────────────────────

  listAuditEvents(projectId?: string, limit = 50): AuditEvent[] {
    const filtered = projectId
      ? this.auditLog.filter(e => e.projectId === projectId)
      : this.auditLog;
    return filtered.slice(-limit).reverse();
  }

  private recordAudit(event: Omit<AuditEvent, "id" | "timestamp">) {
    this.auditLog.push({
      ...event,
      id: nanoid(16),
      timestamp: new Date().toISOString(),
    });
  }
}

/** Singleton — in production, injected via DI container or request context. */
export const store = new Store();
