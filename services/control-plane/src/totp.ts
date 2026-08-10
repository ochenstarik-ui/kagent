import { randomBytes, createHmac, timingSafeEqual, createHash } from "node:crypto";

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32Encode(buffer: Buffer): string {
  let bits = 0;
  let value = 0;
  let output = "";

  for (let i = 0; i < buffer.length; i++) {
    value = (value << 8) | buffer[i]!;
    bits += 8;
    while (bits >= 5) {
      output += BASE32_ALPHABET.charAt((value >>> (bits - 5)) & 31);
      bits -= 5;
    }
  }
  if (bits > 0) {
    output += BASE32_ALPHABET.charAt((value << (5 - bits)) & 31);
  }
  while (output.length % 8 !== 0) {
    output += "=";
  }
  return output;
}

export function base32Decode(input: string): Buffer {
  const cleanedInput = input.toUpperCase().replace(/=/g, "");
  const length = cleanedInput.length;
  let bits = 0;
  let value = 0;
  let index = 0;
  const output = Buffer.alloc(((length * 5) / 8) | 0);

  for (let i = 0; i < length; i++) {
    const val = BASE32_ALPHABET.indexOf(cleanedInput.charAt(i));
    if (val === -1) throw new Error("Invalid base32 character");
    value = (value << 5) | val;
    bits += 5;
    if (bits >= 8) {
      output[index++] = (value >>> (bits - 8)) & 255;
      bits -= 8;
    }
  }
  return output;
}

export function generateSecret(): string {
  return base32Encode(randomBytes(20)).replace(/=/g, "");
}

export function generateRecoveryCodes(): { codes: string[]; hashes: string[] } {
  const codes: string[] = [];
  const hashes: string[] = [];
  for (let i = 0; i < 10; i++) {
    // 128 bits = 16 bytes. We use hex for readability.
    const code = randomBytes(16).toString("hex");
    codes.push(code);
    hashes.push(createHash("sha256").update(code).digest("hex"));
  }
  return { codes, hashes };
}

export function generateUri(email: string, secret: string): string {
  const issuer = encodeURIComponent("KAgent");
  const account = encodeURIComponent(email);
  return `otpauth://totp/${issuer}:${account}?secret=${secret}&issuer=${issuer}`;
}

export function generateCode(secretBuffer: Buffer, timeStep: number): string {
  const timeBuffer = Buffer.alloc(8);
  timeBuffer.writeBigUInt64BE(BigInt(timeStep), 0);

  const hmac = createHmac("sha1", secretBuffer).update(timeBuffer).digest();

  const offset = hmac[hmac.length - 1]! & 0xf;
  const codeInt =
    ((hmac[offset]! & 0x7f) << 24) |
    ((hmac[offset + 1]! & 0xff) << 16) |
    ((hmac[offset + 2]! & 0xff) << 8) |
    (hmac[offset + 3]! & 0xff);

  const code = (codeInt % 1000000).toString().padStart(6, "0");
  return code;
}

export function verifyCodeWithStep(secret: string, code: string, window = 1, currentStepOverride?: number): { valid: boolean; step: number } {
  if (!/^\d{6}$/.test(code)) return { valid: false, step: 0 };

  let secretBuffer: Buffer;
  try {
    secretBuffer = base32Decode(secret);
  } catch {
    return { valid: false, step: 0 };
  }

  const currentStep = currentStepOverride ?? Math.floor(Date.now() / 30000);
  const targetCode = Buffer.from(code);

  for (let i = -window; i <= window; i++) {
    const step = currentStep + i;
    const generated = Buffer.from(generateCode(secretBuffer, step));
    if (generated.length === targetCode.length && timingSafeEqual(generated, targetCode)) {
      return { valid: true, step };
    }
  }
  return { valid: false, step: 0 };
}

import { Pool } from "pg";
import { nanoid } from "nanoid";

export interface TotpStorage {
  createChallenge(challengeId: string, accountId: string, expiresAt: number): Promise<void>;
  getChallenge(challengeId: string): Promise<{ accountId: string; expiresAt: number; attempts: number } | undefined>;
  incrementChallengeAttempts(challengeId: string): Promise<void>;
  deleteChallenge(challengeId: string): Promise<void>;
  getLastStep(accountId: string): Promise<number>;
  setLastStep(accountId: string, step: number): Promise<void>;
  deleteLastStep(accountId: string): Promise<void>;
}

export class InMemoryTotpStorage implements TotpStorage {
  private _challenges = new Map<string, { accountId: string; expiresAt: number; attempts: number }>();
  private _totpLastSteps = new Map<string, number>();

  async createChallenge(challengeId: string, accountId: string, expiresAt: number) {
    this._challenges.set(challengeId, { accountId, expiresAt, attempts: 0 });
  }
  async getChallenge(challengeId: string) {
    return this._challenges.get(challengeId);
  }
  async incrementChallengeAttempts(challengeId: string) {
    const ch = this._challenges.get(challengeId);
    if (ch) ch.attempts++;
  }
  async deleteChallenge(challengeId: string) {
    this._challenges.delete(challengeId);
  }
  async getLastStep(accountId: string) {
    return this._totpLastSteps.get(accountId) ?? -1;
  }
  async setLastStep(accountId: string, step: number) {
    this._totpLastSteps.set(accountId, step);
  }
  async deleteLastStep(accountId: string) {
    this._totpLastSteps.delete(accountId);
  }
}

export class PostgresTotpStorage implements TotpStorage {
  constructor(private pool: Pool) {}
  async createChallenge(challengeId: string, accountId: string, expiresAt: number) {
    await this.pool.query(
      "INSERT INTO totp_challenges (id, account_id, expires_at) VALUES ($1, $2, to_timestamp($3))",
      [challengeId, accountId, expiresAt / 1000.0]
    );
  }
  async getChallenge(challengeId: string) {
    const res = await this.pool.query("SELECT * FROM totp_challenges WHERE id = $1", [challengeId]);
    if (res.rows.length === 0) return undefined;
    const row = res.rows[0];
    return { accountId: row.account_id, expiresAt: new Date(row.expires_at).getTime(), attempts: row.attempts };
  }
  async incrementChallengeAttempts(challengeId: string) {
    await this.pool.query("UPDATE totp_challenges SET attempts = attempts + 1 WHERE id = $1", [challengeId]);
  }
  async deleteChallenge(challengeId: string) {
    await this.pool.query("DELETE FROM totp_challenges WHERE id = $1", [challengeId]);
  }
  async getLastStep(accountId: string) {
    const res = await this.pool.query("SELECT totp_last_step FROM accounts WHERE id = $1", [accountId]);
    if (res.rows.length === 0 || !res.rows[0].totp_last_step) return -1;
    return parseInt(res.rows[0].totp_last_step, 10);
  }
  async setLastStep(accountId: string, step: number) {
    await this.pool.query("UPDATE accounts SET totp_last_step = $1 WHERE id = $2", [step, accountId]);
  }
  async deleteLastStep(accountId: string) {
    await this.pool.query("UPDATE accounts SET totp_last_step = NULL WHERE id = $1", [accountId]);
  }
}

export class TotpPolicy {
  constructor(private storage: TotpStorage) {}

  async createChallenge(accountId: string): Promise<string> {
    const challengeId = nanoid(20);
    const expiresAt = Date.now() + 5 * 60 * 1000;
    await this.storage.createChallenge(challengeId, accountId, expiresAt);
    return challengeId;
  }

  async getAndVerifyChallenge(challengeId: string): Promise<{ accountId: string } | { error: string }> {
    const challenge = await this.storage.getChallenge(challengeId);
    if (!challenge || challenge.expiresAt < Date.now() || challenge.attempts >= 5) {
      return { error: "Invalid credentials" };
    }
    return { accountId: challenge.accountId };
  }

  async failChallenge(challengeId: string): Promise<void> {
    await this.storage.incrementChallengeAttempts(challengeId);
  }

  async finishChallenge(challengeId: string): Promise<void> {
    await this.storage.deleteChallenge(challengeId);
  }

  async consumeTotpCode(accountId: string, secret: string, code: string): Promise<boolean> {
    const { valid, step } = verifyCodeWithStep(secret, code);
    if (!valid) return false;

    const lastStep = await this.storage.getLastStep(accountId);
    if (step <= lastStep) return false;

    await this.storage.setLastStep(accountId, step);
    return true;
  }
  
  async resetLastStep(accountId: string): Promise<void> {
    await this.storage.deleteLastStep(accountId);
  }
}
