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

export interface TaskExecutionContract {
  schemaVersion: "1";
  projectId: string;
  taskId: string;
  objective: string;
  capability?: string;
  contextRefs: string[];
  allowedPaths: string[];
  requiredChecks: string[];
  limits: WorkspaceLimits;
  issuedAt: string;
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
  taskContract: TaskExecutionContract;
  contractDigest: string;
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
  allowedPaths?: string[];
  requiredChecks?: string[];
}

export interface WorkspaceLease {
  workspaceId: string;
  workerId: string;
  generation: number;
  acquiredAt: string;
  heartbeatAt: string;
  expiresAt: string;
}

export interface WorkspaceLeaseGrant extends WorkspaceLease {
  leaseToken: string;
  taskContract: TaskExecutionContract;
  contractDigest: string;
}

export interface ProvisioningRecord {
  workspaceId: string;
  workerId: string;
  checkoutRef: string;
  headSha?: string;
  status: "ready" | "failed" | "cleaned";
  lastError?: string;
  updatedAt: string;
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
