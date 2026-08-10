/** Auth database adapter — accounts, sessions, project membership. */

import { Pool } from "pg";
import { nanoid } from "nanoid";
import { createHash } from "node:crypto";
import {
  hashPassword as hashPw,
  verifyPassword,
  generateTokens,
  hashRefreshToken,
  type TokenPayload,
  type AuthTokens,
  type LoginChallenge,
} from "./auth.js";
import { TotpPolicy, InMemoryTotpStorage, PostgresTotpStorage, generateRecoveryCodes as genRecoveryCodes } from "./totp.js";

export class AuthStore {
  private totpPolicy: TotpPolicy;

  constructor(private pool: Pool) {
    if (process.env.NODE_ENV === "test") {
      this.totpPolicy = new TotpPolicy(new InMemoryTotpStorage());
    } else {
      this.totpPolicy = new TotpPolicy(new PostgresTotpStorage(pool));
    }
  }

  // ── Registration ──────────────────────────

  async register(email: string, password: string): Promise<{ account: any; tokens: AuthTokens } | { error: string }> {
    // Check existing
    const existing = await this.pool.query("SELECT id FROM accounts WHERE email = $1", [email]);
    if (existing.rows.length > 0) {
      return { error: "Email already registered" };
    }

    const id = nanoid(12);
    const passwordHash = await hashPw(password);
    const result = await this.pool.query(
      `INSERT INTO accounts (id, email, password_hash) VALUES ($1, $2, $3) RETURNING *`,
      [id, email, passwordHash]
    );
    const account = result.rows[0];

    // Create session
    const session = await this._createSession(id);
    const tokens = generateTokens({
      sub: account.id,
      email: account.email,
      role: account.role,
      sessionId: session.id,
    });

    // Store refresh token hash
    await this.pool.query(
      "UPDATE sessions SET refresh_token_hash = $1 WHERE id = $2",
      [hashRefreshToken(tokens.refreshToken), session.id]
    );

    return { account: { id: account.id, email: account.email, role: account.role }, tokens };
  }

  // ── Login ─────────────────────────────────

  async login(email: string, password: string): Promise<{ account: any; tokens: AuthTokens } | { account: any; challenge: LoginChallenge } | { error: string }> {
    const result = await this.pool.query(
      "SELECT * FROM accounts WHERE email = $1 AND disabled_at IS NULL",
      [email]
    );
    if (result.rows.length === 0) {
      return { error: "Invalid credentials" };
    }

    const account = result.rows[0];
    const valid = await verifyPassword(password, account.password_hash);
    if (!valid) {
      return { error: "Invalid credentials" };
    }

    if (account.totp_enabled) {
      const challengeId = await this.totpPolicy.createChallenge(account.id);
      return {
        account: { id: account.id, email: account.email, role: account.role },
        challenge: { challengeId }
      };
    }

    // Create session
    const session = await this._createSession(account.id);
    const tokens = generateTokens({
      sub: account.id,
      email: account.email,
      role: account.role,
      sessionId: session.id,
    });

    await this.pool.query(
      "UPDATE sessions SET refresh_token_hash = $1 WHERE id = $2",
      [hashRefreshToken(tokens.refreshToken), session.id]
    );

    return {
      account: { id: account.id, email: account.email, role: account.role },
      tokens,
    };
  }

  // ── Refresh ───────────────────────────────

  async refresh(refreshToken: string): Promise<AuthTokens | { error: string }> {
    const hash = hashRefreshToken(refreshToken);
    const result = await this.pool.query(
      `SELECT * FROM sessions WHERE refresh_token_hash = $1 AND expires_at > now() AND revoked_at IS NULL`,
      [hash]
    );
    if (result.rows.length === 0) {
      return { error: "Invalid or expired refresh token" };
    }

    const session = result.rows[0];
    const account = await this.pool.query("SELECT * FROM accounts WHERE id = $1", [session.account_id]);
    if (account.rows.length === 0 || account.rows[0].disabled_at) {
      return { error: "Account disabled" };
    }

    // Rotate refresh token
    await this.pool.query("UPDATE sessions SET revoked_at = now() WHERE id = $1", [session.id]);

    // New session
    const newSession = await this._createSession(session.account_id);
    const tokens = generateTokens({
      sub: account.rows[0].id,
      email: account.rows[0].email,
      role: account.rows[0].role,
      sessionId: newSession.id,
    });

    await this.pool.query(
      "UPDATE sessions SET refresh_token_hash = $1 WHERE id = $2",
      [hashRefreshToken(tokens.refreshToken), newSession.id]
    );

    return tokens;
  }

  // ── Logout ────────────────────────────────

  async logout(sessionId: string): Promise<void> {
    await this.pool.query("UPDATE sessions SET revoked_at = now() WHERE id = $1", [sessionId]);
  }

  async logoutAll(accountId: string): Promise<void> {
    await this.pool.query(
      "UPDATE sessions SET revoked_at = now() WHERE account_id = $1 AND revoked_at IS NULL",
      [accountId]
    );
  }

  // ── TOTP ──────────────────────────────────

  async getTotpStatus(accountId: string): Promise<{ secret: string | null; enabled: boolean }> {
    const res = await this.pool.query("SELECT totp_secret, totp_enabled FROM accounts WHERE id = $1", [accountId]);
    if (res.rows.length === 0) return { secret: null, enabled: false };
    return { secret: res.rows[0].totp_secret, enabled: res.rows[0].totp_enabled };
  }

  async saveTotpSecret(accountId: string, secret: string): Promise<void> {
    await this.pool.query("UPDATE accounts SET totp_secret = $1 WHERE id = $2", [secret, accountId]);
    await this.totpPolicy.resetLastStep(accountId);
  }

  async activateTotp(accountId: string): Promise<void> {
    await this.pool.query("UPDATE accounts SET totp_enabled = true WHERE id = $1", [accountId]);
  }

  async disableTotp(accountId: string): Promise<void> {
    await this.pool.query("UPDATE accounts SET totp_enabled = false, totp_secret = NULL WHERE id = $1", [accountId]);
    await this.pool.query("DELETE FROM recovery_codes WHERE account_id = $1", [accountId]);
    await this.totpPolicy.resetLastStep(accountId);
  }

  async generateRecoveryCodes(accountId: string): Promise<string[]> {
    const { codes, hashes } = genRecoveryCodes();
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      await client.query("DELETE FROM recovery_codes WHERE account_id = $1", [accountId]);
      for (const hash of hashes) {
        await client.query("INSERT INTO recovery_codes (account_id, code_hash) VALUES ($1, $2)", [accountId, hash]);
      }
      await client.query("COMMIT");
    } catch (err) {
      await client.query("ROLLBACK");
      throw err;
    } finally {
      client.release();
    }
    return codes;
  }

  async consumeTotpCode(accountId: string, secret: string, code: string): Promise<boolean> {
    return this.totpPolicy.consumeTotpCode(accountId, secret, code);
  }

  async loginWithTotp(challengeId: string, code: string): Promise<{ account: any; tokens: AuthTokens } | { error: string }> {
    const challengeCheck = await this.totpPolicy.getAndVerifyChallenge(challengeId);
    if ("error" in challengeCheck) {
      return challengeCheck;
    }

    const res = await this.pool.query("SELECT * FROM accounts WHERE id = $1 AND disabled_at IS NULL", [challengeCheck.accountId]);
    if (res.rows.length === 0) {
      await this.totpPolicy.failChallenge(challengeId);
      return { error: "Invalid credentials" };
    }
    const account = res.rows[0];

    if (!account.totp_enabled || !account.totp_secret) {
      await this.totpPolicy.failChallenge(challengeId);
      return { error: "Invalid credentials" };
    }

    let valid = false;
    if (code.length === 6) {
      valid = await this.totpPolicy.consumeTotpCode(account.id, account.totp_secret, code);
    } else {
      const codeHash = createHash("sha256").update(code).digest("hex");
      const delRes = await this.pool.query("DELETE FROM recovery_codes WHERE account_id = $1 AND code_hash = $2 RETURNING 1", [account.id, codeHash]);
      valid = delRes.rowCount !== null && delRes.rowCount > 0;
    }

    if (!valid) {
      await this.totpPolicy.failChallenge(challengeId);
      return { error: "Invalid credentials" };
    }

    await this.totpPolicy.finishChallenge(challengeId);

    const session = await this._createSession(account.id);
    const tokens = generateTokens({
      sub: account.id,
      email: account.email,
      role: account.role,
      sessionId: session.id,
    });

    await this.pool.query(
      "UPDATE sessions SET refresh_token_hash = $1 WHERE id = $2",
      [hashRefreshToken(tokens.refreshToken), session.id]
    );

    return {
      account: { id: account.id, email: account.email, role: account.role },
      tokens,
    };
  }

  async verifyAccountPassword(accountId: string, password: string): Promise<boolean> {
    const res = await this.pool.query("SELECT password_hash FROM accounts WHERE id = $1", [accountId]);
    if (res.rows.length === 0) return false;
    return verifyPassword(password, res.rows[0].password_hash);
  }
  // ── Membership ────────────────────────────

  async addMember(projectId: string, accountId: string, role: string): Promise<void> {
    await this.pool.query(
      `INSERT INTO project_members (project_id, account_id, role) VALUES ($1, $2, $3)
       ON CONFLICT (project_id, account_id) DO UPDATE SET role = $3`,
      [projectId, accountId, role]
    );
  }

  async getMemberRole(projectId: string, accountId: string): Promise<string | null> {
    const result = await this.pool.query(
      "SELECT role FROM project_members WHERE project_id = $1 AND account_id = $2",
      [projectId, accountId]
    );
    return result.rows[0]?.role ?? null;
  }

  async isSessionValid(sessionId: string, accountId: string): Promise<boolean> {
    const result = await this.pool.query(
      "SELECT 1 FROM sessions WHERE id = $1 AND account_id = $2 AND revoked_at IS NULL AND expires_at > now()",
      [sessionId, accountId]
    );
    return result.rows.length > 0;
  }

  // ── Helpers ───────────────────────────────

  private async _createSession(accountId: string) {
    const result = await this.pool.query(
      `INSERT INTO sessions (id, account_id, refresh_token_hash, expires_at)
       VALUES ($1, $2, 'pending', now() + interval '30 days') RETURNING *`,
      [nanoid(20), accountId]
    );
    return result.rows[0];
  }
}
