export type WorkspaceStatus =
  | "provisioning"
  | "ready"
  | "running"
  | "paused"
  | "awaiting_approval"
  | "verifying"
  | "completed"
  | "failed"
  | "cancelled";

export type WorkspaceSessionKind = "agent" | "terminal" | "browser";
export type WorkspaceSessionStatus =
  | "starting"
  | "active"
  | "waiting"
  | "stopped"
  | "failed";

export interface WorkspaceLimits {
  maxRuntimeMinutes: number;
  maxChangedFiles: number;
  maxConcurrentAgents: number;
  networkAccess: "denied" | "allowlisted";
}

export interface Workspace {
  id: string;
  projectId: string;
  taskId: string;
  status: WorkspaceStatus;
  repositoryUrl: string;
  baseBranch: string;
  branchName: string;
  workspaceRef: string;
  limits: WorkspaceLimits;
  changedFiles: number;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceSession {
  id: string;
  workspaceId: string;
  kind: WorkspaceSessionKind;
  title: string;
  status: WorkspaceSessionStatus;
  agentHarness?: string;
  createdAt: string;
  updatedAt: string;
}

export interface DiffReviewComment {
  id: string;
  workspaceId: string;
  path: string;
  line: number;
  side: "old" | "new";
  body: string;
  status: "open" | "resolved";
  authorId: string;
  createdAt: string;
  resolvedAt?: string;
}

export interface CreateWorkspaceInput {
  baseBranch?: string;
  limits?: Partial<WorkspaceLimits>;
}

export interface CreateSessionInput {
  kind: WorkspaceSessionKind;
  title: string;
  agentHarness?: string;
}

export interface CreateReviewCommentInput {
  path: string;
  line: number;
  side: "old" | "new";
  body: string;
}
