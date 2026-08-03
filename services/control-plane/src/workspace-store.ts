import { nanoid } from "nanoid";
import type {
  CreateReviewCommentInput,
  CreateSessionInput,
  CreateWorkspaceInput,
  DiffReviewComment,
  Workspace,
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
    return parsed.toString();
  }

  if (/^[\w.-]+@[\w.-]+:[\w./-]+$/u.test(trimmed)) return trimmed;
  throw new Error("repositoryUrl must be HTTPS, SSH, Git or SCP-style");
}

export class WorkspaceStore {
  private workspaces = new Map<string, Workspace>();
  private sessions = new Map<string, WorkspaceSession>();
  private comments = new Map<string, DiffReviewComment>();

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
    input: CreateWorkspaceInput = {}
  ): Workspace {
    const existing = this.listWorkspaces({ taskId }).find(workspace =>
      !["completed", "failed", "cancelled"].includes(workspace.status)
    );
    if (existing) {
      throw new Error("Task already has an active workspace");
    }

    const id = nanoid(12);
    const now = new Date().toISOString();
    const workspace: Workspace = {
      id,
      projectId,
      taskId,
      status: "provisioning",
      repositoryUrl: sanitizeRepositoryUrl(repositoryUrl),
      baseBranch: input.baseBranch?.trim() || "main",
      branchName: `agent/${safeBranchPart(taskTitle)}-${taskId.slice(0, 8)}`,
      workspaceRef: `workspace:${id}`,
      limits: { ...DEFAULT_LIMITS, ...input.limits },
      changedFiles: 0,
      createdAt: now,
      updatedAt: now
    };

    this.validateLimits(workspace.limits);
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
