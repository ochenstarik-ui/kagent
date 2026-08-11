/** Auth routes — register, login, refresh, logout, session management. */

import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { AuthStore } from "./auth-db.js";
import { authMiddleware, type AuthenticatedRequest } from "./auth.js";
import { generateSecret, generateUri } from "./totp.js";
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

    if ("challenge" in result) {
      return reply.status(202).send({ challengeId: result.challenge.challengeId });
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

  // ── TOTP ──────────────────────────────────

  app.post("/v1/auth/totp/enroll", { preHandler: [authMiddleware] }, async (req: FastifyRequest, reply: FastifyReply) => {
    const principal = (req as AuthenticatedRequest).principal!;
    const status = await authStore.getTotpStatus(principal.sub);
    if (status.enabled) {
      return reply.status(400).send({ code: "invalid_state", message: "TOTP already enabled" });
    }

    const secret = generateSecret();
    await authStore.saveTotpSecret(principal.sub, secret);
    return { secret, uri: generateUri(principal.email, secret) };
  });

  app.post("/v1/auth/totp/activate", { preHandler: [authMiddleware] }, async (req: FastifyRequest, reply: FastifyReply) => {
    const { code } = req.body as { code?: string };
    if (!code) return reply.status(400).send({ code: "invalid_input", message: "code required" });

    const principal = (req as AuthenticatedRequest).principal!;
    const status = await authStore.getTotpStatus(principal.sub);
    if (status.enabled) {
      // Allow regeneration if enabled and correct password+code provided.
      // But wait! This endpoint takes only `code`, not `password`!
      // Actually let's just make `activate` also return `codes` initially.
      // If it's already enabled, it should regenerate if `password` is provided.
      const { password } = req.body as { password?: string };
      if (!password) {
        return reply.status(400).send({ code: "invalid_state", message: "TOTP already enabled" });
      }
      const validPassword = await authStore.verifyAccountPassword(principal.sub, password);
      if (!validPassword || !status.secret || !(await authStore.consumeTotpCode(principal.sub, status.secret, code))) {
        return reply.status(401).send({ code: "unauthorized", message: "Invalid credentials" });
      }
      const codes = await authStore.generateRecoveryCodes(principal.sub);
      return { status: "recovery_codes_regenerated", codes };
    }
    
    if (!status.secret) {
      return reply.status(400).send({ code: "invalid_state", message: "Not enrolled" });
    }
    if (!(await authStore.consumeTotpCode(principal.sub, status.secret, code))) {
      return reply.status(400).send({ code: "invalid_code", message: "Invalid code" });
    }

    await authStore.activateTotp(principal.sub);
    const codes = await authStore.generateRecoveryCodes(principal.sub);
    return { status: "totp_activated", codes };
  });

  app.post("/v1/auth/totp/disable", { preHandler: [authMiddleware] }, async (req: FastifyRequest, reply: FastifyReply) => {
    const { password, code } = req.body as { password?: string; code?: string };
    if (!password || !code) {
      return reply.status(400).send({ code: "invalid_input", message: "password and code required" });
    }

    const principal = (req as AuthenticatedRequest).principal!;
    const validPassword = await authStore.verifyAccountPassword(principal.sub, password);
    const status = await authStore.getTotpStatus(principal.sub);
    
    let valid = false;
    if (status.enabled && status.secret) {
      if (code.length === 6) {
        valid = await authStore.consumeTotpCode(principal.sub, status.secret, code);
      } else {
        // Technically disable doesn't consume recovery codes in the prompt, but it could.
        // The prompt says "disable TOTP revokes the set"
        valid = code.length > 6; // just let it pass or maybe check? 
        // Wait, "disable TOTP revokes the set." It doesn't say it requires recovery code.
        // Assuming we require a valid TOTP code to disable.
      }
    }
    
    if (
      !validPassword ||
      !status.enabled ||
      !status.secret ||
      !(await authStore.consumeTotpCode(principal.sub, status.secret, code))
    ) {
      return reply.status(401).send({ code: "unauthorized", message: "Invalid credentials" });
    }

    await authStore.disableTotp(principal.sub);
    return { status: "totp_disabled" };
  });

  app.post("/v1/auth/login/totp", async (req: FastifyRequest, reply: FastifyReply) => {
    const { challengeId, code } = req.body as { challengeId?: string; code?: string };
    if (!challengeId || !code) {
      return reply.status(400).send({ code: "invalid_input", message: "challengeId and code required" });
    }

    const result = await authStore.loginWithTotp(challengeId, code);
    if ("error" in result) {
      return reply.status(401).send({ code: "unauthorized", message: "Invalid credentials" });
    }

    return { account: result.account, tokens: result.tokens };
  });
}
