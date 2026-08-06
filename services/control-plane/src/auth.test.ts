import { describe, it, expect } from "vitest";
import {
  hashPassword,
  verifyPassword,
  generateTokens,
  validateAccessToken,
  authMiddleware,
  requireRole,
  type TokenPayload,
} from "./auth.js";

function replyStub() {
  const status = (code: number) => ({
    send: (payload: unknown) => ({ code, payload }),
  });
  return { status } as unknown as { status: (code: number) => { send: (payload: unknown) => { code: number; payload: unknown } } };
}

describe("auth", () => {
  it("hashPassword / verifyPassword round-trip", async () => {
    const stored = await hashPassword("correct horse battery staple");
    expect(stored).toMatch(/^pbkdf2:[a-f0-9]{32}:[a-f0-9]{128}$/);
    expect(await verifyPassword("correct horse battery staple", stored)).toBe(true);
    expect(await verifyPassword("wrong password", stored)).toBe(false);
  });

  it("returns 401 without bearer token", async () => {
    const req = { headers: {} } as Parameters<typeof authMiddleware>[0];
    const reply = replyStub();
    const result = await authMiddleware(req, reply as Parameters<typeof authMiddleware>[1]);
    expect((result as { code: number }).code).toBe(401);
  });

  it("rejects invalid bearer token", async () => {
    const req = { headers: { authorization: "Bearer invalid-token" } } as Parameters<typeof authMiddleware>[0];
    const reply = replyStub();
    const result = await authMiddleware(req, reply as Parameters<typeof authMiddleware>[1]);
    expect((result as { code: number }).code).toBe(401);
  });

  it("accepts valid bearer token and attaches principal", async () => {
    const payload: Omit<TokenPayload, "iat" | "exp"> = {
      sub: "acc_123",
      email: "test@example.com",
      role: "developer",
      sessionId: "sess_456",
    };
    const { accessToken } = generateTokens(payload);

    const req = { headers: { authorization: `Bearer ${accessToken}` } } as Parameters<typeof authMiddleware>[0];
    const reply = { status: () => ({ send: (v: unknown) => v }) } as unknown as Parameters<typeof authMiddleware>[1];
    await authMiddleware(req, reply);
    expect((req as { principal?: TokenPayload }).principal).toMatchObject({
      sub: payload.sub,
      email: payload.email,
      role: payload.role,
      sessionId: payload.sessionId,
    });
  });

  it("requireRole enforces role", async () => {
    const req = { principal: { role: "developer" } } as unknown as Parameters<ReturnType<typeof requireRole>>[0];
    const reply = {
      status: (code: number) => ({ send: (payload: unknown) => ({ code, payload }) }),
    } as unknown as Parameters<ReturnType<typeof requireRole>>[1];

    const allowed = requireRole("admin", "developer");
    expect(await allowed(req, reply)).toBeUndefined();

    const denied = requireRole("admin");
    const result = await denied(req, reply);
    expect((result as { code: number }).code).toBe(403);
  });
});
