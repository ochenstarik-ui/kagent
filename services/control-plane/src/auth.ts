/** Authentication module — JWT, bcrypt, session management. */

import { randomBytes, createHash, timingSafeEqual } from "node:crypto";
import { createSigner, createVerifier } from "fast-jwt";
import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";

// ── Config ────────────────────────────────

const JWT_SECRET = process.env["JWT_SECRET"] ?? "dev-secret-change-in-production-min-32-chars!!";
const ACCESS_TOKEN_TTL = "15m";
const REFRESH_TOKEN_TTL_DAYS = 30;
const BCRYPT_ROUNDS = 12;

// ── JWT ───────────────────────────────────

const signAccess = createSigner({
  key: JWT_SECRET,
  algorithm: "HS256",
  expiresIn: ACCESS_TOKEN_TTL, // 15 minutes
});

const signRefresh = createSigner({
  key: JWT_SECRET,
  algorithm: "HS256",
  expiresIn: `${REFRESH_TOKEN_TTL_DAYS}d`,
});

const verifyToken = createVerifier({
  key: JWT_SECRET,
  algorithms: ["HS256"],
});

export interface TokenPayload {
  sub: string;       // account_id
  email: string;
  role: string;
  sessionId: string;
  iat: number;
  exp: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

// ── Password ──────────────────────────────

export async function hashPassword(password: string): Promise<string> {
  // Use Node crypto pbkdf2 as bcrypt alternative (no native deps)
  const salt = randomBytes(16).toString("hex");
  const hash = await pbkdf2(password, salt);
  return `pbkdf2:${salt}:${hash}`;
}

export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  const [, salt, expectedHash] = stored.split(":");
  const hash = await pbkdf2(password, salt);
  return timingSafeEqual(Buffer.from(hash), Buffer.from(expectedHash));
}

function pbkdf2(password: string, salt: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const crypto = require("node:crypto") as typeof import("node:crypto");
    crypto.pbkdf2(
      password,
      salt,
      100_000,
      64,
      "sha512",
      (err: Error | null, derivedKey: Buffer) => {
        if (err) reject(err);
        else resolve(derivedKey.toString("hex"));
      }
    );
  });
}

// ── Token generation ──────────────────────

export function generateTokens(payload: Omit<TokenPayload, "iat" | "exp">): AuthTokens {
  const accessToken = signAccess(payload);
  const refreshToken = signRefresh(payload);
  return {
    accessToken,
    refreshToken,
    expiresIn: 900, // 15 min in seconds
  };
}

export function validateAccessToken(token: string): TokenPayload | null {
  try {
    return verifyToken(token) as TokenPayload;
  } catch {
    return null;
  }
}

export function hashRefreshToken(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

// ── Middleware ─────────────────────────────

export interface AuthenticatedRequest extends FastifyRequest {
  principal?: TokenPayload;
}

export async function authMiddleware(req: FastifyRequest, reply: FastifyReply) {
  const header = req.headers.authorization;
  if (!header?.startsWith("Bearer ")) {
    return reply.status(401).send({ code: "unauthorized", message: "Missing or invalid token" });
  }

  const token = header.slice(7);
  const payload = validateAccessToken(token);
  if (!payload) {
    return reply.status(401).send({ code: "unauthorized", message: "Token expired or invalid" });
  }

  (req as AuthenticatedRequest).principal = payload;
}

export function requireRole(...roles: string[]) {
  return async (req: FastifyRequest, reply: FastifyReply) => {
    const principal = (req as AuthenticatedRequest).principal;
    if (!principal) {
      return reply.status(401).send({ code: "unauthorized" });
    }
    if (!roles.includes(principal.role)) {
      return reply.status(403).send({ code: "forbidden", message: `Requires role: ${roles.join(" or ")}` });
    }
  };
}

export const requireAdmin = requireRole("admin", "system");
export const requireSystem = requireRole("system");
