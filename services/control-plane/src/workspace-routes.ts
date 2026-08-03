import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { store } from "./store.js";
import type {
  CreateReviewCommentInput,
  CreateSessionInput,
  CreateWorkspaceInput,
  WorkspaceStatus
} from "./workspace-domain.js";
import { workspaceStore } from "./workspace-store.js";

function actorId(req: FastifyRequest): string {
  return (req.headers["x-actor-id"] as string) ?? "anonymous";
}

function invalid(reply: FastifyReply, message: string) {
  return reply.status(422).send({ code: "invalid_workspace_operation", message });
}

export async function registerWorkspaceRoutes(app: FastifyInstance) {
  app.get("/v1/workspaces", async (req: FastifyRequest) => {
    const query = req.query as { projectId?: string; taskId?: string };
    const items = workspaceStore.listWorkspaces(query);
    return { items, total: items.length };
  });

  app.get("/v1/workspaces/:id/cockpit", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const cockpit = workspaceStore.cockpit(id);
    if (!cockpit) return reply.status(404).send({ code: "not_found", message: "Workspace not found" });
    return cockpit;
  });

  app.post("/v1/tasks/:taskId/workspace", async (req: FastifyRequest, reply: FastifyReply) => {
    const { taskId } = req.params as { taskId: string };
    const task = store.getTask(taskId);
    if (!task) return reply.status(404).send({ code: "not_found", message: "Task not found" });
    const project = store.getProject(task.projectId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    if (!project.repositoryUrl) return invalid(reply, "Project repositoryUrl is required");

    try {
      const workspace = workspaceStore.createWorkspace(
        project.id,
        task.id,
        project.repositoryUrl,
        task.title,
        (req.body ?? {}) as CreateWorkspaceInput
      );
      return reply.status(201).send(workspace);
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post("/v1/workspaces/:id/transition", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { status } = req.body as { status: WorkspaceStatus };
    const result = workspaceStore.transitionWorkspace(id, status);
    if (result.error) return invalid(reply, result.error);
    return result.workspace;
  });

  app.get("/v1/workspaces/:id/sessions", async (req: FastifyRequest) => {
    const { id } = req.params as { id: string };
    const items = workspaceStore.listSessions(id);
    return { items, total: items.length };
  });

  app.post("/v1/workspaces/:id/sessions", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const input = req.body as CreateSessionInput;
    if (!input.kind || !input.title?.trim()) return invalid(reply, "kind and title are required");
    try {
      return reply.status(201).send(workspaceStore.createSession(id, input));
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.get("/v1/workspaces/:id/review-comments", async (req: FastifyRequest) => {
    const { id } = req.params as { id: string };
    const items = workspaceStore.listComments(id);
    return { items, total: items.length };
  });

  app.post("/v1/workspaces/:id/review-comments", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const input = req.body as CreateReviewCommentInput;
    if (!input.path?.trim() || !input.body?.trim() || !input.side) {
      return invalid(reply, "path, line, side and body are required");
    }
    try {
      return reply.status(201).send(workspaceStore.createComment(id, input, actorId(req)));
    } catch (error) {
      return invalid(reply, (error as Error).message);
    }
  });

  app.post(
    "/v1/workspaces/:id/review-comments/:commentId/resolve",
    async (req: FastifyRequest, reply: FastifyReply) => {
      const { id, commentId } = req.params as { id: string; commentId: string };
      const comment = workspaceStore.resolveComment(id, commentId);
      if (!comment) return reply.status(404).send({ code: "not_found", message: "Review comment not found" });
      return comment;
    }
  );
}
