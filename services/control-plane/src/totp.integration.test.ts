import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Pool } from "pg";
import { AuthStore } from "./auth-db.js";
import { PostgresTotpStorage, TotpPolicy } from "./totp.js";
import { hashPassword } from "./auth.js";
import { base32Decode, base32Encode, generateCode } from "./totp.js";
import { nanoid } from "nanoid";

const dbUrl = process.env["DATABASE_URL"];

describe.skipIf(!dbUrl)("TOTP PostgreSQL Integration Tests", () => {
  let pool: Pool;

  beforeAll(async () => {
    pool = new Pool({ connectionString: dbUrl });
  });

  afterAll(async () => {
    if (pool) await pool.end();
  });

  it("proves cross-instance replay rejection, atomic one-time challenge, and lock after 5 attempts", async () => {
    const store1 = new AuthStore(pool);
    // @ts-ignore - overriding policy to force Postgres
    store1.totpPolicy = new TotpPolicy(new PostgresTotpStorage(pool));
    
    const store2 = new AuthStore(pool);
    // @ts-ignore
    store2.totpPolicy = new TotpPolicy(new PostgresTotpStorage(pool));

    const email = `test-${nanoid(8)}@example.com`;
    const password = "correct horse battery staple";
    const secret = base32Encode(Buffer.from("12345678901234567890", "ascii")).replace(/=/g, "");

    const registerRes = await store1.register(email, password);
    expect("error" in registerRes).toBe(false);
    
    // @ts-ignore
    const accountId = registerRes.account.id;

    await pool.query("UPDATE accounts SET totp_enabled = true, totp_secret = $1 WHERE id = $2", [secret, accountId]);

    const firstLogin = await store1.login(email, password);
    expect("challenge" in firstLogin).toBe(true);
    // @ts-ignore
    const challengeId = firstLogin.challenge.challengeId;

    // Prove lock after 5 attempts
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const res = await store1.loginWithTotp(challengeId, "000000");
      expect(res).toEqual({ error: "Invalid credentials" });
    }

    // 6th attempt should fail even if correct code, because it's locked
    const step = Math.floor(Date.now() / 30_000);
    const code = generateCode(base32Decode(secret), step);
    const lockedRes = await store1.loginWithTotp(challengeId, code);
    expect(lockedRes).toEqual({ error: "Invalid credentials" });

    // Prove cross-instance replay rejection & atomic one-time challenge
    const secondLogin = await store2.login(email, password);
    expect("challenge" in secondLogin).toBe(true);
    // @ts-ignore
    const challengeId2 = secondLogin.challenge.challengeId;

    // Successfully consume challenge on store1
    const completed = await store1.loginWithTotp(challengeId2, code);
    expect("tokens" in completed).toBe(true);

    // Challenge should be gone (atomic one-time challenge)
    const challengeReuseRes = await store2.loginWithTotp(challengeId2, code);
    expect(challengeReuseRes).toEqual({ error: "Invalid credentials" });

    // Try to login again and reuse the same code (replay rejection)
    const thirdLogin = await store2.login(email, password);
    // @ts-ignore
    const challengeId3 = thirdLogin.challenge.challengeId;

    // Replay the code on store2 (cross-instance)
    const replayRes = await store2.loginWithTotp(challengeId3, code);
    expect(replayRes).toEqual({ error: "Invalid credentials" });
  });
});
