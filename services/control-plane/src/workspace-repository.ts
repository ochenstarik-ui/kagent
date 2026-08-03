import type {
  CreateReviewCommentInput,
  CreateSessionInput,
  CreateWorkspaceInput,
  DiffReviewComment,
  TaskExecutionContract,
  Workspace,
  WorkspaceLeaseGrant,
  ProvisioningRecord,
  WorkspaceSession,
  WorkspaceStatus
} from "./workspace-domain.js";

export type Awaitable<T> = T | Promise<T>;

export interface WorkspaceRepository {
  listWorkspaces(filters?: { projectId?: string; taskId?: string }): Awaitable<Workspace[]>;
  getWorkspace(id: string): Awaitable<Workspace | undefined>;
  createWorkspace(
    projectId: string,
    taskId: string,
    repositoryUrl: string,
    taskTitle: string,
    input?: CreateWorkspaceInput,
    taskContext?: { objective?: string; capability?: string; contextRefs?: string[] }
  ): Awaitable<Workspace>;
  transitionWorkspace(
    id: string,
    status: WorkspaceStatus
  ): Awaitable<{ workspace?: Workspace; error?: string }>;
  acquireLease(
    workspaceId: string,
    workerId: string,
    ttlSeconds?: number,
    now?: Date
  ): Awaitable<WorkspaceLeaseGrant>;
  heartbeatLease(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    ttlSeconds?: number,
    now?: Date
  ): Awaitable<{
    workspaceId: string;
    workerId: string;
    generation: number;
    acquiredAt: string;
    heartbeatAt: string;
    expiresAt: string;
  }>;
  releaseLease(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    now?: Date
  ): Awaitable<void>;
  recordProvisioning(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    input: {
      checkoutRef: string;
      headSha?: string;
      status: "ready" | "failed" | "cleaned";
      lastError?: string;
    },
    now?: Date
  ): Awaitable<ProvisioningRecord>;
  listSessions(workspaceId: string): Awaitable<WorkspaceSession[]>;
  createSession(workspaceId: string, input: CreateSessionInput): Awaitable<WorkspaceSession>;
  listComments(workspaceId: string): Awaitable<DiffReviewComment[]>;
  createComment(
    workspaceId: string,
    input: CreateReviewCommentInput,
    authorId: string
  ): Awaitable<DiffReviewComment>;
  resolveComment(
    workspaceId: string,
    commentId: string
  ): Awaitable<DiffReviewComment | undefined>;
  cockpit(workspaceId: string): Awaitable<
    | {
        workspace: Workspace;
        sessions: WorkspaceSession[];
        review: { openComments: number; resolvedComments: number };
        controls: { canPause: boolean; canResume: boolean; canCancel: boolean };
      }
    | undefined
  >;
}

export function hashableTaskContract(contract: TaskExecutionContract): string {
  return JSON.stringify(contract);
}
