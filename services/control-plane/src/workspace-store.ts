import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { nanoid } from "nanoid";
import { canonicalJson } from "./canonical-json.js";
import type {
  CreateReviewCommentInput,
  CreateSessionInput,
  CreateWorkspaceInput,
  DiffReviewComment,
  Workspace,
  WorkspaceLeaseGrant,
  ProvisioningRecord,
  WorkspaceLimits,
  WorkspaceSession,
  WorkspaceStatus
} from "./workspace-domain.js";

const DEFAULT_LIMITS: WorkspaceLimits = {
  maxRuntimeMinutes: 120,
  maxChangedFiles: 30,
  maxConcurrentAgents: 1,
  networkAccess: "denied"
};

const WORKSPACE_TRANSITIONS: Record<WorkspaceStatus, WorkspaceStatus[]> = {
  provisioning: ["ready", "failed", "cancelled"],
  ready: ["running", "failed", "cancelled"],
  running: ["paused", "awaiting_approval", "verifying", "failed", "cancelled"],
  paused: ["running", "failed", "cancelled"],
  awaiting_approval: ["running", "failed", "cancelled"],
  verifying: ["completed", "running", "failed", "cancelled"],
  completed: [],
  failed: [],
  cancelled: []
};

function safeBranchPart(value: string): string {
  const normalized = value
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/gu, "-")
    .replace(/^-+|-+$/gu, "");
  return normalized.slice(0, 48) || "task";
}

function sanitizeRepositoryUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) throw new Error("repositoryUrl is required");

  if (/^[a-z][a-z0-9+.-]*:\/\//iu.test(trimmed)) {
    const parsed = new URL(trimmed);
    if (!["https:", "ssh:", "git:"].includes(parsed.protocol)) {
      throw new Error("repositoryUrl protocol is not allowed");
    }
    parsed.username = "";
    parsed.password = "";
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  }

  if (/^[\w.-]+@[\w.-]+:[\w./-]+$/u.test(trimmed)) return trimmed;
  throw new Error("repositoryUrl must be HTTPS, SSH, Git or SCP-style");
}

export class WorkspaceStore {
  private workspaces = new Map<string, Workspace>();
  private sessions = new Map<string, WorkspaceSession>();
  private comments = new Map<string, DiffReviewComment>();
  private provisioning = new Map<string, ProvisioningRecord>();
  private leases = new Map<string, {
    workerId: string;
    tokenHash: string;
    generation: number;
    acquiredAt: string;
    heartbeatAt: string;
    expiresAt: string;
  }>();

  listWorkspaces(filters: { projectId?: string; taskId?: string } = {}): Workspace[] {
    return [...this.workspaces.values()].filter(workspace =>
      (!filters.projectId || workspace.projectId === filters.projectId) &&
      (!filters.taskId || workspace.taskId === filters.taskId)
    );
  }

  getWorkspace(id: string): Workspace | undefined {
    return this.workspaces.get(id);
  }

  createWorkspace(
    projectId: string,
    taskId: string,
    repositoryUrl: string,
    taskTitle: string,
    input: CreateWorkspaceInput = {},
    taskContext: { objective?: string; capability?: string; contextRefs?: string[] } = {}
  ): Workspace {
    const existing = this.listWorkspaces({ taskId }).find(workspace =>
      !["completed", "failed", "cancelled"].includes(workspace.status)
    );
    if (existing) {
      throw new Error("Task already has an active workspace");
    }

    const id = nanoid(12);
    const now = new Date().toISOString();
    const limits = { ...DEFAULT_LIMITS, ...input.limits };
    this.validateLimits(limits);
    const allowedPaths = this.validateRelativeList(input.allowedPaths ?? ["**"]);
    const requiredChecks = this.validateChecks(input.requiredChecks ?? []);
    const taskContract = {
      schemaVersion: "1" as const,
      projectId,
      taskId,
      objective: taskContext.objective?.trim() || taskTitle.trim(),
      ...(taskContext.capability?.trim()
        ? { capability: taskContext.capability.trim() }
        : {}),
      contextRefs: [...(taskContext.contextRefs ?? [])],
      allowedPaths,
      requiredChecks,
      limits,
      issuedAt: now
    };
    const contractDigest = createHash("sha256")
      .update(canonicalJson(taskContract))
      .digest("hex");
    const workspace: Workspace = {
      id,
      projectId,
      taskId,
      status: "provisioning",
      repositoryUrl: sanitizeRepositoryUrl(repositoryUrl),
      baseBranch: input.baseBranch?.trim() || "main",
      branchName: "agent/" + safeBranchPart(taskTitle) + "-" + taskId.slice(0, 8),
      workspaceRef: "workspace:" + id,
      limits,
      changedFiles: 0,
      taskContract,
      contractDigest,
      createdAt: now,
      updatedAt: now
    };

    this.workspaces.set(id, workspace);
    return workspace;
  }
  transitionWorkspace(
    id: string,
    status: WorkspaceStatus
  ): { workspace?: Workspace; error?: string } {
    const workspace = this.workspaces.get(id);
    if (!workspace) return { error: "Workspace not found" };

    if (!WORKSPACE_TRANSITIONS[workspace.status].includes(status)) {
      return {
        error: `Invalid workspace transition: ${workspace.status} -> ${status}`
      };
    }

    workspace.status = status;
    workspace.updatedAt = new Date().toISOString();
    return { workspace };
  }

  acquireLease(
    workspaceId: string,
    workerId: string,
    ttlSeconds = 60,
    now = new Date()
  ): WorkspaceLeaseGrant {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) throw new Error("Workspace not found");
    this.validateLeaseInput(workerId, ttlSeconds);

    const existing = this.leases.get(workspaceId);
    if (existing && new Date(existing.expiresAt).getTime() > now.getTime()) {
      throw new Error("Workspace already has an active lease");
    }

    const leaseToken = randomBytes(32).toString("base64url");
    const timestamp = now.toISOString();
    const generation = (existing?.generation ?? 0) + 1;
    const lease = {
      workerId: workerId.trim(),
      tokenHash: createHash("sha256").update(leaseToken).digest("hex"),
      generation,
      acquiredAt: timestamp,
      heartbeatAt: timestamp,
      expiresAt: new Date(now.getTime() + ttlSeconds * 1000).toISOString()
    };
    this.leases.set(workspaceId, lease);
    return {
      workspaceId,
      workerId: lease.workerId,
      generation,
      acquiredAt: timestamp,
      heartbeatAt: timestamp,
      expiresAt: lease.expiresAt,
      leaseToken,
      taskContract: workspace.taskContract,
      contractDigest: workspace.contractDigest
    };
  }

  heartbeatLease(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    ttlSeconds = 60,
    now = new Date()
  ) {
    const lease = this.requireLease(workspaceId, workerId, leaseToken, now);
    this.validateLeaseInput(workerId, ttlSeconds);
    lease.heartbeatAt = now.toISOString();
    lease.expiresAt = new Date(now.getTime() + ttlSeconds * 1000).toISOString();
    return {
      workspaceId,
      workerId: lease.workerId,
      generation: lease.generation,
      acquiredAt: lease.acquiredAt,
      heartbeatAt: lease.heartbeatAt,
      expiresAt: lease.expiresAt
    };
  }

  releaseLease(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    now = new Date()
  ): void {
    this.requireLease(workspaceId, workerId, leaseToken, now);
    this.leases.delete(workspaceId);
  }

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
    now = new Date()
  ): ProvisioningRecord {
    this.requireLease(workspaceId, workerId, leaseToken, now);
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) throw new Error("Workspace not found");
    if (input.checkoutRef !== "checkout:" + workspaceId) {
      throw new Error("checkoutRef does not match workspace identity");
    }
    if (
      !["ready", "failed", "cleaned"].includes(input.status) ||
      (input.status === "ready" && !/^[0-9a-f]{40,64}$/u.test(input.headSha ?? ""))
    ) {
      throw new Error("Provisioning result is invalid");
    }
    if ((input.lastError?.length ?? 0) > 4000) {
      throw new Error("Provisioning error exceeds 4000 characters");
    }

    const record: ProvisioningRecord = {
      workspaceId,
      workerId,
      checkoutRef: input.checkoutRef,
      ...(input.headSha ? { headSha: input.headSha } : {}),
      status: input.status,
      ...(input.lastError ? { lastError: input.lastError } : {}),
      updatedAt: now.toISOString()
    };
    this.provisioning.set(workspaceId, record);
    if (input.status === "ready" && workspace.status === "provisioning") {
      workspace.status = "ready";
    } else if (input.status === "failed" && !["completed", "failed", "cancelled"].includes(workspace.status)) {
      workspace.status = "failed";
    } else if (input.status === "cleaned" && !["completed", "failed", "cancelled"].includes(workspace.status)) {
      workspace.status = "cancelled";
    }
    workspace.updatedAt = now.toISOString();
    return record;
  }
  listSessions(workspaceId: string): WorkspaceSession[] {
    return [...this.sessions.values()].filter(session => session.workspaceId === workspaceId);
  }

  createSession(workspaceId: string, input: CreateSessionInput): WorkspaceSession {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) throw new Error("Workspace not found");
    if (!["agent", "terminal", "browser"].includes(input.kind)) {
      throw new Error("Unsupported workspace session kind");
    }
    if (!input.title.trim()) {
      throw new Error("Workspace session title is required");
    }

    const activeAgents = this.listSessions(workspaceId).filter(
      session => session.kind === "agent" && ["starting", "active", "waiting"].includes(session.status)
    ).length;
    if (input.kind === "agent" && activeAgents >= workspace.limits.maxConcurrentAgents) {
      throw new Error("Workspace agent concurrency limit reached");
    }

    const now = new Date().toISOString();
    const session: WorkspaceSession = {
      id: nanoid(12),
      workspaceId,
      kind: input.kind,
      title: input.title.trim(),
      status: "starting",
      ...(input.agentHarness?.trim()
        ? { agentHarness: input.agentHarness.trim() }
        : {}),
      createdAt: now,
      updatedAt: now
    };
    this.sessions.set(session.id, session);
    return session;
  }

  listComments(workspaceId: string): DiffReviewComment[] {
    return [...this.comments.values()].filter(comment => comment.workspaceId === workspaceId);
  }

  createComment(
    workspaceId: string,
    input: CreateReviewCommentInput,
    authorId: string
  ): DiffReviewComment {
    if (!this.workspaces.has(workspaceId)) throw new Error("Workspace not found");
    if (input.line < 1 || !Number.isInteger(input.line)) {
      throw new Error("Review line must be a positive integer");
    }
    if (!["old", "new"].includes(input.side)) {
      throw new Error("Review side must be old or new");
    }
    if (input.path.startsWith("/") || input.path.includes("..")) {
      throw new Error("Review path must be repository-relative");
    }

    const comment: DiffReviewComment = {
      id: nanoid(12),
      workspaceId,
      path: input.path,
      line: input.line,
      side: input.side,
      body: input.body.trim(),
      status: "open",
      authorId,
      createdAt: new Date().toISOString()
    };
    this.comments.set(comment.id, comment);
    return comment;
  }

  resolveComment(workspaceId: string, commentId: string): DiffReviewComment | undefined {
    const comment = this.comments.get(commentId);
    if (!comment || comment.workspaceId !== workspaceId) return undefined;
    comment.status = "resolved";
    comment.resolvedAt = new Date().toISOString();
    return comment;
  }

  cockpit(workspaceId: string) {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) return undefined;
    const sessions = this.listSessions(workspaceId);
    const comments = this.listComments(workspaceId);
    return {
      workspace,
      provisioning: this.provisioning.get(workspaceId),
      sessions,
      review: {
        openComments: comments.filter(comment => comment.status === "open").length,
        resolvedComments: comments.filter(comment => comment.status === "resolved").length
      },
      controls: {
        canPause: workspace.status === "running",
        canResume: workspace.status === "paused",
        canCancel: !["completed", "failed", "cancelled"].includes(workspace.status)
      }
    };
  }

  private validateRelativeList(paths: string[]): string[] {
    if (paths.length < 1 || paths.length > 128) {
      throw new Error("allowedPaths must contain between 1 and 128 entries");
    }
    return paths.map(path => {
      const value = path.trim().replaceAll("\\", "/");
      if (!value || value.startsWith("/") || /(^|\/)\.\.?($|\/)/u.test(value)) {
        throw new Error("allowedPaths must be repository-relative");
      }
      return value;
    });
  }

  private validateChecks(checks: string[]): string[] {
    if (checks.length > 32) throw new Error("requiredChecks cannot exceed 32 entries");
    return checks.map(check => {
      const value = check.trim();
      if (!value || value.length > 256 || /[\r\n\0]/u.test(value)) {
        throw new Error("requiredChecks contains an invalid command");
      }
      return value;
    });
  }

  private validateLeaseInput(workerId: string, ttlSeconds: number): void {
    if (!/^[a-zA-Z0-9._:-]{1,128}$/u.test(workerId.trim())) {
      throw new Error("workerId is invalid");
    }
    if (!Number.isInteger(ttlSeconds) || ttlSeconds < 15 || ttlSeconds > 300) {
      throw new Error("ttlSeconds must be between 15 and 300");
    }
  }

  private requireLease(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    now: Date
  ) {
    const lease = this.leases.get(workspaceId);
    if (!lease || new Date(lease.expiresAt).getTime() <= now.getTime()) {
      throw new Error("Workspace lease is missing or expired");
    }
    const actual = Buffer.from(createHash("sha256").update(leaseToken).digest("hex"));
    const expected = Buffer.from(lease.tokenHash);
    if (
      workerId !== lease.workerId ||
      actual.length !== expected.length ||
      !timingSafeEqual(actual, expected)
    ) {
      throw new Error("Workspace lease credentials are invalid");
    }
    return lease;
  }
  private validateLimits(limits: WorkspaceLimits): void {
    if (limits.maxRuntimeMinutes < 1 || limits.maxRuntimeMinutes > 1440) {
      throw new Error("maxRuntimeMinutes must be between 1 and 1440");
    }
    if (limits.maxChangedFiles < 1 || limits.maxChangedFiles > 1000) {
      throw new Error("maxChangedFiles must be between 1 and 1000");
    }
    if (limits.maxConcurrentAgents < 1 || limits.maxConcurrentAgents > 16) {
      throw new Error("maxConcurrentAgents must be between 1 and 16");
    }
    if (!["denied", "allowlisted"].includes(limits.networkAccess)) {
      throw new Error("networkAccess must be denied or allowlisted");
    }
  }
}

export const workspaceStore = new WorkspaceStore();
