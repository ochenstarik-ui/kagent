import type {
  ProjectId,
  ReviewCommentId,
  TaskId,
  WorkspaceId,
  WorkspaceSessionId
} from "./ids.js";

export const workspaceStatuses = [
  "provisioning",
  "ready",
  "running",
  "paused",
  "awaiting_approval",
  "verifying",
  "completed",
  "failed",
  "cancelled"
] as const;

export type WorkspaceStatus = (typeof workspaceStatuses)[number];

export const workspaceSessionKinds = ["agent", "terminal", "browser"] as const;
export type WorkspaceSessionKind = (typeof workspaceSessionKinds)[number];

export const workspaceSessionStatuses = [
  "starting",
  "active",
  "waiting",
  "stopped",
  "failed"
] as const;
export type WorkspaceSessionStatus = (typeof workspaceSessionStatuses)[number];

export interface WorkspaceLimits {
  readonly maxRuntimeMinutes: number;
  readonly maxChangedFiles: number;
  readonly maxConcurrentAgents: number;
  readonly networkAccess: "denied" | "allowlisted";
}

export interface AgentWorkspace {
  readonly id: WorkspaceId;
  readonly projectId: ProjectId;
  readonly taskId: TaskId;
  readonly status: WorkspaceStatus;
  readonly repositoryUrl: string;
  readonly baseBranch: string;
  readonly branchName: string;
  /** Opaque worker-owned reference. Host filesystem paths must not be exposed. */
  readonly workspaceRef: string;
  readonly limits: WorkspaceLimits;
  readonly changedFiles: number;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface WorkspaceSession {
  readonly id: WorkspaceSessionId;
  readonly workspaceId: WorkspaceId;
  readonly kind: WorkspaceSessionKind;
  readonly title: string;
  readonly status: WorkspaceSessionStatus;
  readonly agentHarness?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface DiffReviewComment {
  readonly id: ReviewCommentId;
  readonly workspaceId: WorkspaceId;
  readonly path: string;
  readonly line: number;
  readonly side: "old" | "new";
  readonly body: string;
  readonly status: "open" | "resolved";
  readonly authorId: string;
  readonly createdAt: string;
  readonly resolvedAt?: string;
}

const allowedWorkspaceTransitions: Readonly<
  Record<WorkspaceStatus, readonly WorkspaceStatus[]>
> = {
  provisioning: ["ready", "failed", "cancelled"],
  ready: ["running", "cancelled", "failed"],
  running: ["paused", "awaiting_approval", "verifying", "failed", "cancelled"],
  paused: ["running", "cancelled", "failed"],
  awaiting_approval: ["running", "cancelled", "failed"],
  verifying: ["completed", "running", "failed", "cancelled"],
  completed: [],
  failed: [],
  cancelled: []
};

export function canTransitionWorkspace(
  from: WorkspaceStatus,
  to: WorkspaceStatus
): boolean {
  return allowedWorkspaceTransitions[from].includes(to);
}

export function assertWorkspaceTransition(
  from: WorkspaceStatus,
  to: WorkspaceStatus
): void {
  if (!canTransitionWorkspace(from, to)) {
    throw new Error(`Invalid workspace transition: ${from} -> ${to}`);
  }
}
