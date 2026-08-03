/** Control Plane API routes — project + task CRUD + audit. */

import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { store } from "./store.js";
import type {
  CreateProjectInput,
  CreateTaskInput,
  UpdateTaskStatusInput,
  PaginationParams,
} from "./domain.js";
import { KAGENT_VERSION } from "./version.js";

export async function registerRoutes(app: FastifyInstance) {
  // ── Health ────────────────────────────────────

  app.get("/health/live", async () => ({
    status: "alive",
    service: "control-plane",
    version: KAGENT_VERSION,
  }));

  app.get("/health/ready", async () => ({
    status: "ready",
    projects: store.listProjects().length,
    tasks: store.listTasks().length,
  }));

  // ── Projects ──────────────────────────────────

  app.get("/v1/projects", async (req: FastifyRequest) => {
    const { offset, limit } = req.query as PaginationParams;
    const all = store.listProjects();
    const page = all.slice(offset ?? 0, (offset ?? 0) + (limit ?? 50));
    return { items: page, total: all.length };
  });

  app.get("/v1/projects/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const project = store.getProject(id);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    return project;
  });

  app.post("/v1/projects", async (req: FastifyRequest, reply: FastifyReply) => {
    const input = req.body as CreateProjectInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    if (!input.name || !input.description) {
      return reply.status(400).send({ code: "invalid_input", message: "name and description required" });
    }
    const project = store.createProject(input, actorId);
    return reply.status(201).send(project);
  });

  app.patch("/v1/projects/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    const project = store.updateProject(id, req.body as Record<string, unknown>, actorId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    return project;
  });

  // ── Tasks ─────────────────────────────────────

  app.get("/v1/tasks", async (req: FastifyRequest) => {
    const { projectId } = req.query as { projectId?: string };
    const tasks = store.listTasks(projectId);
    return { items: tasks, total: tasks.length };
  });

  app.get("/v1/tasks/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const task = store.getTask(id);
    if (!task) return reply.status(404).send({ code: "not_found", message: "Task not found" });
    return task;
  });

  app.post("/v1/tasks", async (req: FastifyRequest, reply: FastifyReply) => {
    const input = req.body as CreateTaskInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    if (!input.projectId || !input.title) {
      return reply.status(400).send({ code: "invalid_input", message: "projectId and title required" });
    }
    const project = store.getProject(input.projectId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    const task = store.createTask(input, actorId);
    return reply.status(201).send(task);
  });

  app.patch("/v1/tasks/:id/status", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { status, reason } = req.body as UpdateTaskStatusInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    const result = store.updateTaskStatus(id, status, actorId, reason);
    if (result.error) return reply.status(422).send({ code: "invalid_transition", message: result.error });
    return result.task;
  });

  // ── Audit ─────────────────────────────────────

  app.get("/v1/audit", async (req: FastifyRequest) => {
    const { projectId, limit } = req.query as { projectId?: string; limit?: number };
    const events = store.listAuditEvents(projectId, limit);
    return { items: events, total: events.length };
  });

  // ── System ────────────────────────────────────

  app.get("/v1/system/info", async () => ({
    name: "KAgent Control Plane",
    version: KAGENT_VERSION,
    apiVersion: "v1",
    uptime: process.uptime(),
  }));
}
