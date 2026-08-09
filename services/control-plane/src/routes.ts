/** Control Plane API routes — project + task CRUD + audit. */

import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { getStore, PostgresStore } from "./db.js";
import type {
  CreateProjectInput,
  CreateTaskInput,
  UpdateTaskStatusInput,
  PaginationParams,
} from "./domain.js";

export async function registerRoutes(app: FastifyInstance, store: PostgresStore = getStore()) {
  // Error shielding handler for internal database/server errors
  app.setErrorHandler((error: Error & { statusCode?: number }, req: FastifyRequest, reply: FastifyReply) => {
    req.log.error(error);
    const statusCode = error.statusCode && error.statusCode < 500 ? error.statusCode : 500;
    if (statusCode >= 500) {
      return reply.status(500).send({
        code: "internal_error",
        message: "Internal server error",
        requestId: req.id,
      });
    }
    return reply.status(statusCode).send({
      code: error.name ?? "error",
      message: error.message,
    });
  });

  // ── Health ────────────────────────────────────

  app.get("/health/live", async () => ({
    status: "alive",
    service: "control-plane",
    version: "0.2.0",
  }));

  app.get("/health/ready", async (_req: FastifyRequest, reply: FastifyReply) => {
    const isHealthy = await store.healthCheck();
    if (!isHealthy) {
      return reply.status(503).send({
        status: "unhealthy",
        message: "Database connection unavailable",
      });
    }
    const [projectsCount, tasksCount] = await Promise.all([
      store.countProjects(),
      store.countTasks(),
    ]);
    return {
      status: "ready",
      projects: projectsCount,
      tasks: tasksCount,
    };
  });

  // ── Projects ──────────────────────────────────

  app.get("/v1/projects", async (req: FastifyRequest) => {
    const { offset, limit } = req.query as PaginationParams;
    const { items, total } = await store.listProjects(offset, limit);
    return { items, total };
  });

  app.get("/v1/projects/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const project = await store.getProject(id);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    return project;
  });

  app.post("/v1/projects", async (req: FastifyRequest, reply: FastifyReply) => {
    const input = req.body as CreateProjectInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    if (!input.name || !input.description) {
      return reply.status(400).send({ code: "invalid_input", message: "name and description required" });
    }
    const project = await store.createProject(input, actorId);
    return reply.status(201).send(project);
  });

  app.patch("/v1/projects/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    const project = await store.updateProject(id, req.body as Record<string, unknown>, actorId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    return project;
  });

  // ── Tasks ─────────────────────────────────────

  app.get("/v1/tasks", async (req: FastifyRequest) => {
    const { projectId, offset, limit } = req.query as { projectId?: string; offset?: number; limit?: number };
    const { items, total } = await store.listTasks(projectId, offset, limit);
    return { items, total };
  });

  app.get("/v1/tasks/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const task = await store.getTask(id);
    if (!task) return reply.status(404).send({ code: "not_found", message: "Task not found" });
    return task;
  });

  app.post("/v1/tasks", async (req: FastifyRequest, reply: FastifyReply) => {
    const input = req.body as CreateTaskInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    if (!input.projectId || !input.title) {
      return reply.status(400).send({ code: "invalid_input", message: "projectId and title required" });
    }
    const project = await store.getProject(input.projectId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    const task = await store.createTask(input, actorId);
    return reply.status(201).send(task);
  });

  app.patch("/v1/tasks/:id/status", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { status, reason } = req.body as UpdateTaskStatusInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    const result = await store.updateTaskStatus(id, status, actorId, reason);
    if (result.error) return reply.status(422).send({ code: "invalid_transition", message: result.error });
    return result.task;
  });

  // ── Audit ─────────────────────────────────────

  app.get("/v1/audit", async (req: FastifyRequest) => {
    const { projectId, limit } = req.query as { projectId?: string; limit?: number };
    const events = await store.listAuditEvents(projectId, limit);
    return { items: events, total: events.length };
  });

  // ── System ────────────────────────────────────

  app.get("/v1/system/info", async () => ({
    name: "KAgent Control Plane",
    version: "0.2.0",
    apiVersion: "v1",
    uptime: process.uptime(),
  }));
}
