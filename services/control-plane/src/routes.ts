/** Control Plane API routes — project + task CRUD + audit. */

import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { store } from "./store.js";
import type {
  CreateProjectInput,
  CreateTaskInput,
  UpdateTaskStatusInput,
  PaginationParams,
  Project,
  Task,
  AuditEvent,
} from "./domain.js";
import { KAGENT_VERSION } from "./version.js";


interface ControlPlaneRepository {
  listProjects(): Project[] | Promise<Project[]>;
  getProject(id: string): Project | undefined | Promise<Project | undefined>;
  createProject(input: CreateProjectInput, ownerAccountId: string): Project | Promise<Project>;
  updateProject(
    id: string,
    updates: Record<string, unknown>,
    actorId: string
  ): Project | undefined | Promise<Project | undefined>;
  listTasks(projectId?: string): Task[] | Promise<Task[]>;
  getTask(id: string): Task | undefined | Promise<Task | undefined>;
  createTask(input: CreateTaskInput, actorId: string): Task | Promise<Task>;
  updateTaskStatus(
    id: string,
    newStatus: Task["status"],
    actorId: string,
    reason?: string
  ): { task?: Task; error?: string } | Promise<{ task?: Task; error?: string }>;
  listAuditEvents(projectId?: string, limit?: number): AuditEvent[] | Promise<AuditEvent[]>;
}
export async function registerRoutes(
  app: FastifyInstance,
  repository: ControlPlaneRepository = store
) {
  // ── Health ────────────────────────────────────

  app.get("/health/live", async () => ({
    status: "alive",
    service: "control-plane",
    version: KAGENT_VERSION,
  }));

  app.get("/health/ready", async () => ({
    status: "ready",
    projects: (await repository.listProjects()).length,
    tasks: (await repository.listTasks()).length,
  }));

  // ── Projects ──────────────────────────────────

  app.get("/v1/projects", async (req: FastifyRequest) => {
    const { offset, limit } = req.query as PaginationParams;
    const all = await repository.listProjects();
    const page = all.slice(offset ?? 0, (offset ?? 0) + (limit ?? 50));
    return { items: page, total: all.length };
  });

  app.get("/v1/projects/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const project = await repository.getProject(id);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    return project;
  });

  app.post("/v1/projects", async (req: FastifyRequest, reply: FastifyReply) => {
    const input = req.body as CreateProjectInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    if (!input.name || !input.description) {
      return reply.status(400).send({ code: "invalid_input", message: "name and description required" });
    }
    const project = await repository.createProject(input, actorId);
    return reply.status(201).send(project);
  });

  app.patch("/v1/projects/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    const project = await repository.updateProject(id, req.body as Record<string, unknown>, actorId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    return project;
  });

  // ── Tasks ─────────────────────────────────────

  app.get("/v1/tasks", async (req: FastifyRequest) => {
    const { projectId } = req.query as { projectId?: string };
    const tasks = await repository.listTasks(projectId);
    return { items: tasks, total: tasks.length };
  });

  app.get("/v1/tasks/:id", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const task = await repository.getTask(id);
    if (!task) return reply.status(404).send({ code: "not_found", message: "Task not found" });
    return task;
  });

  app.post("/v1/tasks", async (req: FastifyRequest, reply: FastifyReply) => {
    const input = req.body as CreateTaskInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    if (!input.projectId || !input.title) {
      return reply.status(400).send({ code: "invalid_input", message: "projectId and title required" });
    }
    const project = await repository.getProject(input.projectId);
    if (!project) return reply.status(404).send({ code: "not_found", message: "Project not found" });
    const task = await repository.createTask(input, actorId);
    return reply.status(201).send(task);
  });

  app.patch("/v1/tasks/:id/status", async (req: FastifyRequest, reply: FastifyReply) => {
    const { id } = req.params as { id: string };
    const { status, reason } = req.body as UpdateTaskStatusInput;
    const actorId = (req.headers["x-actor-id"] as string) ?? "anonymous";
    const result = await repository.updateTaskStatus(id, status, actorId, reason);
    if (result.error) return reply.status(422).send({ code: "invalid_transition", message: result.error });
    return result.task;
  });

  // ── Audit ─────────────────────────────────────

  app.get("/v1/audit", async (req: FastifyRequest) => {
    const { projectId, limit } = req.query as { projectId?: string; limit?: number };
    const events = await repository.listAuditEvents(projectId, limit);
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
