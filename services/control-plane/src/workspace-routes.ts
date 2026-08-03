import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { store } from "./store.js";
import type { Project, Task } from "./domain.js";
import type {
  CreateReviewCommentInput,
  CreateSessionInput,
  CreateWorkspaceInput,
  WorkspaceStatus
} from "./workspace-domain.js";
import type { WorkspaceRepository } from "./workspace-repository.js";
import { workspaceStore } from "./workspace-store.js";


interface TaskRepository {
  getTask(id: string): Task | undefined | Promise<Task | undefined>;
  getProject(id: string): Project | undefined | Promise<Project | undefined>;
}
function actorId(req: FastifyRequest): string {
  return (req.headers["x-actor-id"] as string) ?? "anonymous";
}

function invalid(reply: FastifyReply, message: string) {
  return reply.status(422).send({ code: "invalid_workspace_operation", message });
}

export async function registerWorkspaceRoutes(
  app: FastifyInstance,
  repository: WorkspaceRepository = workspaceStore,
  taskRepository: TaskRepository = store
) {
  app.get("/v1/workspaces", async (req: FastifyRequest) => {
    const query = req.query as { projectId?: string; taskId?: string };
    const items = await repository.listWorkspaces(query);
    return { items, total: items.length };
  });

  app.get("/v1/workspaces/:id/cockpit", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const cockpit = await repository.cockpit(id);
    if (!cockpit) return reply.status(404).send({ code: "not_found", message: "Workspace not found" });
    return cockpit;
  });

  app.post("/v1/tasks/:taskId/workspace", async (req: FastifyRequest, reply: FastifyReply) => {
    const { taskId } = req.params as { taskId: string };
    const task = await taskRepository.getTask(taskId);
    if (!task) return reply.status(404).send({ code: "not_found", message: "Task not found" });
    const project = await taskRepository.getProject(task.projectId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    if (!project.repositoryUrl) return invalid(reply, "Project repositoryUrl is required");
    if (!["approved", "in_progress"].includes(task.status)) {
      return invalid(reply, "Task must be approved before workspace provisioning");
    }

    try {
      const workspace = await repository.createWorkspace(
        project.id,
        task.id,
        project.repositoryUrl,
        task.title,
        (req.body ?? {}) as CreateWorkspaceInput,
        {
          objective: task.description || task.title,
          ...(task.capability ? { capability: task.capability } : {}),
          contextRefs: task.contextRefs
        }
      );
      return reply.status(201).send(workspace);
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post("/v1/workspaces/:id/transition", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { status } = req.body as { status: WorkspaceStatus };
    const result = await repository.transitionWorkspace(id, status);
    if (result.error) return invalid(reply, result.error);
    return result.workspace;
  });


  app.post("/v1/workspaces/:id/lease", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { workerId, ttlSeconds } = req.body as { workerId?: string; ttlSeconds?: number };
    if (!workerId?.trim()) return invalid(reply, "workerId is required");
    try {
      return reply.status(201).send(
        await repository.acquireLease(id, workerId, ttlSeconds ?? 60)
      );
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post("/v1/workspaces/:id/heartbeat", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { workerId, leaseToken, ttlSeconds } = req.body as {
      workerId?: string;
      leaseToken?: string;
      ttlSeconds?: number;
    };
    if (!workerId?.trim() || !leaseToken) {
      return invalid(reply, "workerId and leaseToken are required");
    }
    try {
      return await repository.heartbeatLease(
        id,
        workerId,
        leaseToken,
        ttlSeconds ?? 60
      );
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post("/v1/workspaces/:id/lease/release", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { workerId, leaseToken } = req.body as {
      workerId?: string;
      leaseToken?: string;
    };
    if (!workerId?.trim() || !leaseToken) {
      return invalid(reply, "workerId and leaseToken are required");
    }
    try {
      await repository.releaseLease(id, workerId, leaseToken);
      return reply.status(204).send();
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post("/v1/workspaces/:id/provisioning", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const input = req.body as {
      workerId?: string;
      leaseToken?: string;
      checkoutRef?: string;
      headSha?: string;
      status?: "ready" | "failed" | "cleaned";
      lastError?: string;
    };
    if (!input.workerId?.trim() || !input.leaseToken || !input.checkoutRef || !input.status) {
      return invalid(reply, "workerId, leaseToken, checkoutRef and status are required");
    }
    try {
      return await repository.recordProvisioning(
        id,
        input.workerId,
        input.leaseToken,
        {
          checkoutRef: input.checkoutRef,
          ...(input.headSha ? { headSha: input.headSha } : {}),
          status: input.status,
          ...(input.lastError ? { lastError: input.lastError } : {})
        }
      );
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });
  app.get("/v1/workspaces/:id/sessions", async (req: FastifyRequest) => {
    const { id } = req.params as { id: string };
    const items = await repository.listSessions(id);
    return { items, total: items.length };
  });

  app.post("/v1/workspaces/:id/sessions", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const input = req.body as CreateSessionInput;
    if (!input.kind || !input.title?.trim()) return invalid(reply, "kind and title are required");
    try {
      return reply.status(201).send(await repository.createSession(id, input));
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.get("/v1/workspaces/:id/review-comments", async (req: FastifyRequest) => {
    const { id } = req.params as { id: string };
    const items = await repository.listComments(id);
    return { items, total: items.length };
  });

  app.post("/v1/workspaces/:id/review-comments", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const input = req.body as CreateReviewCommentInput;
    if (!input.path?.trim() || !input.body?.trim() || !input.side) {
      return invalid(reply, "path, line, side and body are required");
    }
    try {
      return reply.status(201).send(await repository.createComment(id, input, actorId(req)));
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post(
    "/v1/workspaces/:id/review-comments/:commentId/resolve",
    async (req: FastifyRequest, reply: FastifyReply) => {
      const { id, commentId } = req.params as { id: string; commentId: string };
      const comment = await repository.resolveComment(id, commentId);
      if (!comment) return reply.status(404).send({ code: "not_found", message: "Review comment not found" });
      return comment;
    }
  );
}
