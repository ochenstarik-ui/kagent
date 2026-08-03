import { createHash, randomBytes } from "node:crypto";
import { nanoid } from "nanoid";
import { canonicalJson } from "./canonical-json.js";
import type { Pool, PoolClient } from "pg";
import type {
  CreateReviewCommentInput,
  CreateSessionInput,
  CreateWorkspaceInput,
  DiffReviewComment,
  TaskExecutionContract,
  Workspace,
  WorkspaceLeaseGrant,
  WorkspaceLimits,
  WorkspaceSession,
  WorkspaceStatus
} from "./workspace-domain.js";
import type { WorkspaceRepository } from "./workspace-repository.js";

const DEFAULT_LIMITS: WorkspaceLimits = {
  maxRuntimeMinutes: 120,
  maxChangedFiles: 30,
  maxConcurrentAgents: 1,
  networkAccess: "denied"
};

const TRANSITIONS: Record<WorkspaceStatus, WorkspaceStatus[]> = {
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

type DbRow = Record<string, unknown>;

function timestamp(value: unknown): string {
  return value instanceof Date ? value.toISOString() : String(value);
}

function limitsFromRow(row: DbRow): WorkspaceLimits {
  return {
    maxRuntimeMinutes: Number(row["max_runtime_minutes"]),
    maxChangedFiles: Number(row["max_changed_files"]),
    maxConcurrentAgents: Number(row["max_concurrent_agents"]),
    networkAccess: row["network_access"] as WorkspaceLimits["networkAccess"]
  };
}

function workspaceFromRow(row: DbRow): Workspace {
  return {
    id: String(row["id"]),
    projectId: String(row["project_id"]),
    taskId: String(row["task_id"]),
    status: row["status"] as WorkspaceStatus,
    repositoryUrl: String(row["repository_url"]),
    baseBranch: String(row["base_branch"]),
    branchName: String(row["branch_name"]),
    workspaceRef: String(row["workspace_ref"]),
    limits: limitsFromRow(row),
    changedFiles: Number(row["changed_files"]),
    taskContract: row["task_contract"] as TaskExecutionContract,
    contractDigest: String(row["contract_digest"]),
    createdAt: timestamp(row["created_at"]),
    updatedAt: timestamp(row["updated_at"])
  };
}

function sessionFromRow(row: DbRow): WorkspaceSession {
  return {
    id: String(row["id"]),
    workspaceId: String(row["workspace_id"]),
    kind: row["kind"] as WorkspaceSession["kind"],
    title: String(row["title"]),
    status: row["status"] as WorkspaceSession["status"],
    ...(row["agent_harness"] ? { agentHarness: String(row["agent_harness"]) } : {}),
    createdAt: timestamp(row["created_at"]),
    updatedAt: timestamp(row["updated_at"])
  };
}

function commentFromRow(row: DbRow): DiffReviewComment {
  return {
    id: String(row["id"]),
    workspaceId: String(row["workspace_id"]),
    path: String(row["path"]),
    line: Number(row["line"]),
    side: row["side"] as DiffReviewComment["side"],
    body: String(row["body"]),
    status: row["status"] as DiffReviewComment["status"],
    authorId: String(row["author_id"]),
    createdAt: timestamp(row["created_at"]),
    ...(row["resolved_at"] ? { resolvedAt: timestamp(row["resolved_at"]) } : {})
  };
}

function safeBranchPart(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/gu, "-")
      .replace(/^-+|-+$/gu, "")
      .slice(0, 48) || "task"
  );
}

function sanitizeRepositoryUrl(value: string): string {
  const trimmed = value.trim();
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

function validateRelativePaths(paths: string[]): string[] {
  if (paths.length < 1 || paths.length > 128) {
    throw new Error("allowedPaths must contain between 1 and 128 entries");
  }
  return paths.map(path => {
    const normalized = path.trim().replaceAll("\\", "/");
    if (!normalized || normalized.startsWith("/") || /(^|\/)\.\.?($|\/)/u.test(normalized)) {
      throw new Error("allowedPaths must be repository-relative");
    }
    return normalized;
  });
}

function validateChecks(checks: string[]): string[] {
  if (checks.length > 32) throw new Error("requiredChecks cannot exceed 32 entries");
  return checks.map(check => {
    const value = check.trim();
    if (!value || value.length > 256 || /[\r\n\0]/u.test(value)) {
      throw new Error("requiredChecks contains an invalid command");
    }
    return value;
  });
}

function validateLimits(limits: WorkspaceLimits): void {
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

function validateLease(workerId: string, ttlSeconds: number): void {
  if (!/^[a-zA-Z0-9._:-]{1,128}$/u.test(workerId.trim())) {
    throw new Error("workerId is invalid");
  }
  if (!Number.isInteger(ttlSeconds) || ttlSeconds < 15 || ttlSeconds > 300) {
    throw new Error("ttlSeconds must be between 15 and 300");
  }
}

export class PostgresWorkspaceRepository implements WorkspaceRepository {
  constructor(private readonly pool: Pool) {}

  async listWorkspaces(filters: { projectId?: string; taskId?: string } = {}) {
    const clauses: string[] = [];
    const values: string[] = [];
    if (filters.projectId) {
      values.push(filters.projectId);
      clauses.push(`project_id = $${values.length}`);
    }
    if (filters.taskId) {
      values.push(filters.taskId);
      clauses.push(`task_id = $${values.length}`);
    }
    const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
    const result = await this.pool.query(
      `SELECT * FROM agent_workspaces ${where} ORDER BY created_at DESC`,
      values
    );
    return result.rows.map(row => workspaceFromRow(row as DbRow));
  }

  async getWorkspace(id: string) {
    const result = await this.pool.query("SELECT * FROM agent_workspaces WHERE id = $1", [id]);
    return result.rows[0] ? workspaceFromRow(result.rows[0] as DbRow) : undefined;
  }

  async createWorkspace(
    projectId: string,
    taskId: string,
    repositoryUrl: string,
    taskTitle: string,
    input: CreateWorkspaceInput = {},
    taskContext: { objective?: string; capability?: string; contextRefs?: string[] } = {}
  ) {
    const id = nanoid(12);
    const now = new Date().toISOString();
    const limits = { ...DEFAULT_LIMITS, ...input.limits };
    validateLimits(limits);
    const contract: TaskExecutionContract = {
      schemaVersion: "1",
      projectId,
      taskId,
      objective: taskContext.objective?.trim() || taskTitle.trim(),
      ...(taskContext.capability?.trim() ? { capability: taskContext.capability.trim() } : {}),
      contextRefs: [...(taskContext.contextRefs ?? [])],
      allowedPaths: validateRelativePaths(input.allowedPaths ?? ["**"]),
      requiredChecks: validateChecks(input.requiredChecks ?? []),
      limits,
      issuedAt: now
    };
    const digest = createHash("sha256").update(canonicalJson(contract)).digest("hex");
    const result = await this.pool.query(
      `INSERT INTO agent_workspaces (
        id, project_id, task_id, repository_url, base_branch, branch_name,
        workspace_ref, max_runtime_minutes, max_changed_files,
        max_concurrent_agents, network_access, task_contract, contract_digest
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
      RETURNING *`,
      [
        id,
        projectId,
        taskId,
        sanitizeRepositoryUrl(repositoryUrl),
        input.baseBranch?.trim() || "main",
        "agent/" + safeBranchPart(taskTitle) + "-" + taskId.slice(0, 8),
        "workspace:" + id,
        limits.maxRuntimeMinutes,
        limits.maxChangedFiles,
        limits.maxConcurrentAgents,
        limits.networkAccess,
        JSON.stringify(contract),
        digest
      ]
    );
    return workspaceFromRow(result.rows[0] as DbRow);
  }

  async transitionWorkspace(id: string, status: WorkspaceStatus) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const selected = await client.query(
        "SELECT * FROM agent_workspaces WHERE id = $1 FOR UPDATE",
        [id]
      );
      if (!selected.rows[0]) {
        await client.query("ROLLBACK");
        return { error: "Workspace not found" };
      }
      const current = selected.rows[0]["status"] as WorkspaceStatus;
      if (!TRANSITIONS[current].includes(status)) {
        await client.query("ROLLBACK");
        return { error: `Invalid workspace transition: ${current} -> ${status}` };
      }
      const updated = await client.query(
        "UPDATE agent_workspaces SET status = $2, updated_at = now() WHERE id = $1 RETURNING *",
        [id, status]
      );
      await client.query("COMMIT");
      return { workspace: workspaceFromRow(updated.rows[0] as DbRow) };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async acquireLease(workspaceId: string, workerId: string, ttlSeconds = 60, now = new Date()) {
    validateLease(workerId, ttlSeconds);
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const selected = await client.query(
        "SELECT * FROM agent_workspaces WHERE id = $1 FOR UPDATE",
        [workspaceId]
      );
      if (!selected.rows[0]) throw new Error("Workspace not found");
      const existing = await client.query(
        "SELECT * FROM workspace_leases WHERE workspace_id = $1 FOR UPDATE",
        [workspaceId]
      );
      if (
        existing.rows[0] &&
        new Date(existing.rows[0]["expires_at"] as string | Date).getTime() > now.getTime()
      ) {
        throw new Error("Workspace already has an active lease");
      }

      const token = randomBytes(32).toString("base64url");
      const tokenHash = createHash("sha256").update(token).digest("hex");
      const expiresAt = new Date(now.getTime() + ttlSeconds * 1000);
      const generation = Number(existing.rows[0]?.["generation"] ?? 0) + 1;
      const result = await client.query(
        `INSERT INTO workspace_leases (
          workspace_id, worker_id, token_hash, generation, acquired_at,
          heartbeat_at, expires_at, released_at
        ) VALUES ($1,$2,$3,$4,$5,$5,$6,NULL)
        ON CONFLICT (workspace_id) DO UPDATE SET
          worker_id = EXCLUDED.worker_id,
          token_hash = EXCLUDED.token_hash,
          generation = EXCLUDED.generation,
          acquired_at = EXCLUDED.acquired_at,
          heartbeat_at = EXCLUDED.heartbeat_at,
          expires_at = EXCLUDED.expires_at,
          released_at = NULL
        RETURNING *`,
        [workspaceId, workerId.trim(), tokenHash, generation, now, expiresAt]
      );
      await client.query("COMMIT");
      const row = result.rows[0] as DbRow;
      const workspace = workspaceFromRow(selected.rows[0] as DbRow);
      return {
        workspaceId,
        workerId: String(row["worker_id"]),
        generation: Number(row["generation"]),
        acquiredAt: timestamp(row["acquired_at"]),
        heartbeatAt: timestamp(row["heartbeat_at"]),
        expiresAt: timestamp(row["expires_at"]),
        leaseToken: token,
        taskContract: workspace.taskContract,
        contractDigest: workspace.contractDigest
      } satisfies WorkspaceLeaseGrant;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async heartbeatLease(
    workspaceId: string,
    workerId: string,
    leaseToken: string,
    ttlSeconds = 60,
    now = new Date()
  ) {
    validateLease(workerId, ttlSeconds);
    const tokenHash = createHash("sha256").update(leaseToken).digest("hex");
    const result = await this.pool.query(
      `UPDATE workspace_leases
       SET heartbeat_at = $4, expires_at = $5
       WHERE workspace_id = $1 AND worker_id = $2 AND token_hash = $3
         AND released_at IS NULL AND expires_at > $4
       RETURNING *`,
      [workspaceId, workerId, tokenHash, now, new Date(now.getTime() + ttlSeconds * 1000)]
    );
    if (!result.rows[0]) throw new Error("Workspace lease is missing, expired or invalid");
    const row = result.rows[0] as DbRow;
    return {
      workspaceId,
      workerId: String(row["worker_id"]),
      generation: Number(row["generation"]),
      acquiredAt: timestamp(row["acquired_at"]),
      heartbeatAt: timestamp(row["heartbeat_at"]),
      expiresAt: timestamp(row["expires_at"])
    };
  }

  async releaseLease(workspaceId: string, workerId: string, leaseToken: string, now = new Date()) {
    const tokenHash = createHash("sha256").update(leaseToken).digest("hex");
    const result = await this.pool.query(
      `UPDATE workspace_leases SET released_at = $4, expires_at = $4
       WHERE workspace_id = $1 AND worker_id = $2 AND token_hash = $3
         AND released_at IS NULL AND expires_at > $4`,
      [workspaceId, workerId, tokenHash, now]
    );
    if (result.rowCount !== 1) throw new Error("Workspace lease is missing, expired or invalid");
  }


  async recordProvisioning(
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
  ) {
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

    const tokenHash = createHash("sha256").update(leaseToken).digest("hex");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const owned = await client.query(
        "SELECT w.status FROM agent_workspaces w " +
          "JOIN workspace_leases l ON l.workspace_id = w.id " +
          "WHERE w.id = $1 AND l.worker_id = $2 AND l.token_hash = $3 " +
          "AND l.released_at IS NULL AND l.expires_at > $4 FOR UPDATE OF w, l",
        [workspaceId, workerId, tokenHash, now]
      );
      if (!owned.rows[0]) {
        throw new Error("Workspace lease is missing, expired or invalid");
      }
      const result = await client.query(
        "INSERT INTO workspace_provisioning " +
          "(workspace_id, worker_id, checkout_ref, head_sha, status, last_error) " +
          "VALUES ($1,$2,$3,$4,$5,$6) " +
          "ON CONFLICT (workspace_id) DO UPDATE SET " +
          "worker_id = EXCLUDED.worker_id, checkout_ref = EXCLUDED.checkout_ref, " +
          "head_sha = EXCLUDED.head_sha, status = EXCLUDED.status, " +
          "last_error = EXCLUDED.last_error, updated_at = now() RETURNING *",
        [
          workspaceId,
          workerId,
          input.checkoutRef,
          input.headSha ?? null,
          input.status,
          input.lastError ?? null
        ]
      );
      const current = owned.rows[0]["status"] as WorkspaceStatus;
      const terminal = ["completed", "failed", "cancelled"].includes(current);
      const nextStatus =
        input.status === "ready" && current === "provisioning"
          ? "ready"
          : input.status === "failed" && !terminal
            ? "failed"
            : input.status === "cleaned" && !terminal
              ? "cancelled"
              : current;
      await client.query(
        "UPDATE agent_workspaces SET status = $2, updated_at = $3 WHERE id = $1",
        [workspaceId, nextStatus, now]
      );
      await client.query("COMMIT");
      const row = result.rows[0] as DbRow;
      return {
        workspaceId,
        workerId: String(row["worker_id"]),
        checkoutRef: String(row["checkout_ref"]),
        ...(row["head_sha"] ? { headSha: String(row["head_sha"]) } : {}),
        status: row["status"] as "ready" | "failed" | "cleaned",
        ...(row["last_error"] ? { lastError: String(row["last_error"]) } : {}),
        updatedAt: timestamp(row["updated_at"])
      };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
  async listSessions(workspaceId: string) {
    const result = await this.pool.query(
      "SELECT * FROM workspace_sessions WHERE workspace_id = $1 ORDER BY created_at",
      [workspaceId]
    );
    return result.rows.map(row => sessionFromRow(row as DbRow));
  }

  async createSession(workspaceId: string, input: CreateSessionInput) {
    if (!["agent", "terminal", "browser"].includes(input.kind)) {
      throw new Error("Unsupported workspace session kind");
    }
    if (!input.title.trim()) throw new Error("Workspace session title is required");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const workspaceResult = await client.query(
        "SELECT * FROM agent_workspaces WHERE id = $1 FOR UPDATE",
        [workspaceId]
      );
      if (!workspaceResult.rows[0]) throw new Error("Workspace not found");
      if (input.kind === "agent") {
        const active = await client.query(
          `SELECT COUNT(*) FROM workspace_sessions
           WHERE workspace_id = $1 AND kind = 'agent'
             AND status IN ('starting','active','waiting')`,
          [workspaceId]
        );
        const max = Number(workspaceResult.rows[0]["max_concurrent_agents"]);
        if (Number(active.rows[0]["count"]) >= max) {
          throw new Error("Workspace agent concurrency limit reached");
        }
      }
      const result = await client.query(
        `INSERT INTO workspace_sessions (id, workspace_id, kind, title, agent_harness)
         VALUES ($1,$2,$3,$4,$5) RETURNING *`,
        [nanoid(12), workspaceId, input.kind, input.title.trim(), input.agentHarness?.trim() || null]
      );
      await client.query("COMMIT");
      return sessionFromRow(result.rows[0] as DbRow);
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async listComments(workspaceId: string) {
    const result = await this.pool.query(
      "SELECT * FROM diff_review_comments WHERE workspace_id = $1 ORDER BY created_at",
      [workspaceId]
    );
    return result.rows.map(row => commentFromRow(row as DbRow));
  }

  async createComment(workspaceId: string, input: CreateReviewCommentInput, authorId: string) {
    if (!Number.isInteger(input.line) || input.line < 1) {
      throw new Error("Review line must be a positive integer");
    }
    if (!["old", "new"].includes(input.side)) throw new Error("Review side must be old or new");
    const path = validateRelativePaths([input.path])[0];
    if (!input.body.trim()) throw new Error("Review body is required");
    const result = await this.pool.query(
      `INSERT INTO diff_review_comments
       (id, workspace_id, path, line, side, body, author_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *`,
      [nanoid(12), workspaceId, path, input.line, input.side, input.body.trim(), authorId]
    );
    return commentFromRow(result.rows[0] as DbRow);
  }

  async resolveComment(workspaceId: string, commentId: string) {
    const result = await this.pool.query(
      `UPDATE diff_review_comments SET status = 'resolved', resolved_at = now()
       WHERE id = $1 AND workspace_id = $2 RETURNING *`,
      [commentId, workspaceId]
    );
    return result.rows[0] ? commentFromRow(result.rows[0] as DbRow) : undefined;
  }

  async cockpit(workspaceId: string) {
    const workspace = await this.getWorkspace(workspaceId);
    if (!workspace) return undefined;
    const [sessions, comments, provisioningResult] = await Promise.all([
      this.listSessions(workspaceId),
      this.listComments(workspaceId),
      this.pool.query(
        "SELECT * FROM workspace_provisioning WHERE workspace_id = $1",
        [workspaceId]
      )
    ]);
    const provisioningRow = provisioningResult.rows[0] as DbRow | undefined;
    const provisioning = provisioningRow
      ? {
          workspaceId,
          workerId: String(provisioningRow["worker_id"]),
          checkoutRef: String(provisioningRow["checkout_ref"]),
          ...(provisioningRow["head_sha"]
            ? { headSha: String(provisioningRow["head_sha"]) }
            : {}),
          status: provisioningRow["status"] as "ready" | "failed" | "cleaned",
          ...(provisioningRow["last_error"]
            ? { lastError: String(provisioningRow["last_error"]) }
            : {}),
          updatedAt: timestamp(provisioningRow["updated_at"])
        }
      : undefined;
    return {
      workspace,
      provisioning,
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
}
