import type { ProjectId, TaskId } from "./ids.js";

export const taskStatuses = [
  "draft",
  "queued",
  "planning",
  "running",
  "awaiting_approval",
  "verifying",
  "succeeded",
  "failed",
  "cancelled"
] as const;

export type TaskStatus = (typeof taskStatuses)[number];

export interface Task {
  readonly id: TaskId;
  readonly projectId: ProjectId;
  readonly title: string;
  readonly objective: string;
  readonly status: TaskStatus;
  readonly createdAt: string;
  readonly updatedAt: string;
}

const allowedTransitions: Readonly<Record<TaskStatus, readonly TaskStatus[]>> = {
  draft: ["queued", "cancelled"],
  queued: ["planning", "cancelled", "failed"],
  planning: ["running", "awaiting_approval", "failed", "cancelled"],
  running: ["awaiting_approval", "verifying", "failed", "cancelled"],
  awaiting_approval: ["running", "cancelled", "failed"],
  verifying: ["succeeded", "running", "failed", "cancelled"],
  succeeded: [],
  failed: ["queued"],
  cancelled: []
};

export function canTransitionTask(from: TaskStatus, to: TaskStatus): boolean {
  return allowedTransitions[from].includes(to);
}

export function assertTaskTransition(from: TaskStatus, to: TaskStatus): void {
  if (!canTransitionTask(from, to)) {
    throw new Error(`Invalid task transition: ${from} -> ${to}`);
  }
}
