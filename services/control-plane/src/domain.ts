/** Domain types for Control Plane — project and task lifecycle. */

export type ProjectId = string;
export type TaskId = string;
export type AuditId = string;

export type ProjectStatus = "active" | "archived" | "deleted";

export type TaskStatus =
  | "draft"
  | "planned"
  | "approved"
  | "in_progress"
  | "review"
  | "done"
  | "cancelled";

/** Valid status transitions for task state machine */
export const TASK_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  draft: ["planned", "cancelled"],
  planned: ["approved", "cancelled"],
  approved: ["in_progress", "cancelled"],
  in_progress: ["review", "cancelled"],
  review: ["in_progress", "done", "cancelled"],
  done: [],
  cancelled: [],
};

export interface Project {
  id: ProjectId;
  name: string;
  description: string;
  status: ProjectStatus;
  ownerAccountId: string;
  repositoryUrl?: string | undefined;
  createdAt: string;
  updatedAt: string;
}

export interface Task {
  id: TaskId;
  projectId: ProjectId;
  title: string;
  description: string;
  status: TaskStatus;
  assignedAgentId?: string | undefined;
  capability?: string | undefined;
  contextRefs: string[]; // links to artifacts, specs, etc
  createdAt: string;
  updatedAt: string;
}

export interface AuditEvent {
  id: AuditId;
  projectId: ProjectId;
  taskId?: TaskId;
  actorId: string;
  action: string;
  previousState?: string;
  newState?: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface CreateProjectInput {
  name: string;
  description: string;
  repositoryUrl?: string;
}

export interface CreateTaskInput {
  projectId: ProjectId;
  title: string;
  description: string;
  capability?: string;
  contextRefs?: string[];
}

export interface UpdateTaskStatusInput {
  status: TaskStatus;
  reason?: string;
}

export interface PaginationParams {
  offset: number;
  limit: number;
}
