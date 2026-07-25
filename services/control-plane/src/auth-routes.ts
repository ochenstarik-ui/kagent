/** Auth routes — register, login, refresh, logout, session management. */

import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { AuthStore } from "./auth-db.js";
import { authMiddleware, type AuthenticatedRequest } from "./auth.js";
import { Pool } from "pg";

export async function registerAuthRoutes(app: FastifyInstance, pool: Pool) {
  const authStore = new AuthStore(pool);

  // ── Register ──────────────────────────────

  app.post("/v1/auth/register", async (req: FastifyRequest, reply: FastifyReply) => {
    const { email, password } = req.body as { email?: string; password?: string };
    if (!email || !password || password.length < 8) {
      return reply.status(400).send({ code: "invalid_input", message: "email and password (min 8 chars) required" });
    }

    const result = await authStore.register(email, password);
    if ("error" in result) {
      return reply.status(409).send({ code: "conflict", message: result.error });
    }

    // Auto-add owner membership to default projects
    // (in production, first project is created separately)

    return reply.status(201).send({
      account: result.account,
      tokens: result.tokens,
    });
  });

  // ── Login ─────────────────────────────────

  app.post("/v1/auth/login", async (req: FastifyRequest, reply: FastifyReply) => {
    const { email, password } = req.body as { email?: string; password?: string };
    if (!email || !password) {
      return reply.status(400).send({ code: "invalid_input", message: "email and password required" });
    }

    const result = await authStore.login(email, password);
    if ("error" in result) {
      return reply.status(401).send({ code: "unauthorized", message: result.error });
    }

    return {
      account: result.account,
      tokens: result.tokens,
    };
  });

  // ── Refresh ───────────────────────────────

  app.post("/v1/auth/refresh", async (req: FastifyRequest, reply: FastifyReply) => {
    const { refreshToken } = req.body as { refreshToken?: string };
    if (!refreshToken) {
      return reply.status(400).send({ code: "invalid_input", message: "refreshToken required" });
    }

    const result = await authStore.refresh(refreshToken);
    if ("error" in result) {
      return reply.status(401).send({ code: "unauthorized", message: result.error });
    }

    return result;
  });

  // ── Logout ────────────────────────────────

  app.post("/v1/auth/logout", { preHandler: [authMiddleware] }, async (req: FastifyRequest, reply: FastifyReply) => {
    const principal = (req as AuthenticatedRequest).principal!;
    await authStore.logout(principal.sessionId);
    return { status: "logged_out" };
  });

  app.post("/v1/auth/logout-all", { preHandler: [authMiddleware] }, async (req: FastifyRequest, reply: FastifyReply) => {
    const principal = (req as AuthenticatedRequest).principal!;
    await authStore.logoutAll(principal.sub);
    return { status: "all_sessions_revoked" };
  });

  // ── Whoami ────────────────────────────────

  app.get("/v1/auth/whoami", { preHandler: [authMiddleware] }, async (req: FastifyRequest) => {
    const principal = (req as AuthenticatedRequest).principal!;
    return {
      accountId: principal.sub,
      email: principal.email,
      role: principal.role,
      sessionId: principal.sessionId,
    };
  });

  // ── Session validation ────────────────────

  app.get("/v1/auth/sessions", { preHandler: [authMiddleware] }, async (req: FastifyRequest) => {
    const principal = (req as AuthenticatedRequest).principal!;
    const valid = await authStore.isSessionValid(principal.sessionId, principal.sub);
    return { valid, sessionId: principal.sessionId };
  });
}
