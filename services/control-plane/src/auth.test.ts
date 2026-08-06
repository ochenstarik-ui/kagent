import { describe, it, expect, vi } from "vitest";
import {
  hashPassword,
  verifyPassword,
  generateTokens,
  validateAccessToken,
  authMiddleware,
  requireRole,
  type TokenPayload,
} from "./auth.js";

function stubReplyApi() {
  const status = vi.fn<(code: number) => { send: (payload: unknown) => unknown }>();
  const send = vi.fn<(payload: unknown) => unknown>();
  status.mockReturnValue({ send: send as unknown as (payload: unknown) => unknown });
  return { status, send };
}

function stubRequest(headers: Record<string, string>) {
  return { headers } as unknown as Parameters<typeof authMiddleware>[0];
}

describe("auth", () => {
  it("hashPassword / verifyPassword round-trip", async () => {
    const stored = await hashPassword("correct horse battery staple");
    expect(stored).toMatch(/^pbkdf2:[a-f0-9]{32}:[a-f0-9]{128}$/);
    expect(await verifyPassword("correct horse battery staple", stored)).toBe(true);
    expect(await verifyPassword("wrong password", stored)).toBe(false);
  });

  it("returns 401 without bearer token", async () => {
    const reply = stubReplyApi();
    await authMiddleware(
      stubRequest({}),
      reply as unknown as Parameters<typeof authMiddleware>[1]
    );
    expect(reply.status).toHaveBeenCalledWith(401);
  });

  it("rejects invalid bearer token", async () => {
    const reply = stubReplyApi();
    await authMiddleware(
      stubRequest({ authorization: "Bearer invalid-token" }),
      reply as unknown as Parameters<typeof authMiddleware>[1]
    );
    expect(reply.status).toHaveBeenCalledWith(401);
  });

  it("accepts valid bearer token and attaches principal", async () => {
    const payload: Omit<TokenPayload, "iat" | "exp"> = {
      sub: "acc_123",
      email: "test@example.com",
      role: "developer",
      sessionId: "sess_456",
    };
    const { accessToken } = generateTokens(payload);

    const reply = stubReplyApi();
    const req = stubRequest({ authorization: `Bearer ${accessToken}` });
    await authMiddleware(
      req,
      reply as unknown as Parameters<typeof authMiddleware>[1]
    );
    expect(reply.status).not.toHaveBeenCalled();
    const reqRw = req as unknown as { principal?: TokenPayload };
    expect(reqRw.principal).toMatchObject({
      sub: payload.sub,
      email: payload.email,
      role: payload.role,
      sessionId: payload.sessionId,
    });
  });

  it("requireRole enforces role", async () => {
    const req = { principal: { role: "developer" } } as unknown as Parameters<ReturnType<typeof requireRole>>[0];
    const replyAll = stubReplyApi();
    const allowed = requireRole("admin", "developer");
    await allowed(
      req,
      replyAll as unknown as Parameters<ReturnType<typeof requireRole>>[1]
    );
    expect(replyAll.status).not.toHaveBeenCalled();

    const replyDen = stubReplyApi();
    const denied = requireRole("admin");
    await denied(
      req,
      replyDen as unknown as Parameters<ReturnType<typeof requireRole>>[1]
    );
    expect(replyDen.status).toHaveBeenCalledWith(403);
  });
});
