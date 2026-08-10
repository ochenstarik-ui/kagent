import { Pool, type QueryConfig, type QueryResult, type QueryResultRow } from "pg";
import { describe, expect, it, vi } from "vitest";

import { AuthStore } from "./auth-db.js";
import { hashPassword } from "./auth.js";
import { base32Decode, base32Encode, generateCode } from "./totp.js";

function result<Row extends QueryResultRow>(rows: Row[]): QueryResult<Row> {
  return { command: "", rowCount: rows.length, oid: 0, fields: [], rows };
}

function queryText(query: string | QueryConfig): string {
  return typeof query === "string" ? query : query.text;
}

describe("TOTP authentication flow", () => {
  it("consumes an accepted time step only once", async () => {
    const store = new AuthStore(new Pool());
    const secret = base32Encode(Buffer.from("12345678901234567890", "ascii")).replace(/=/g, "");
    const step = Math.floor(Date.now() / 30_000);
    const code = generateCode(base32Decode(secret), step);

    await expect(store.consumeTotpCode("account-1", secret, code)).resolves.toBe(true);
    await expect(store.consumeTotpCode("account-1", secret, code)).resolves.toBe(false);
  });

  it("withholds tokens, locks invalid challenges, and rejects replay generically", async () => {
    const password = "correct horse battery staple";
    const secret = base32Encode(Buffer.from("12345678901234567890", "ascii")).replace(/=/g, "");
    const account = {
      id: "account-1",
      email: "person@example.com",
      role: "developer",
      password_hash: await hashPassword(password),
      totp_enabled: true,
      totp_secret: secret,
      disabled_at: null,
    };
    const pool = new Pool();
    let sessionSequence = 0;
    vi.spyOn(pool, "query").mockImplementation(async (query: string | QueryConfig) => {
      const text = queryText(query);
      if (text.includes("FROM accounts WHERE email")) return result([account]);
      if (text.includes("FROM accounts WHERE id")) return result([account]);
      if (text.startsWith("INSERT INTO sessions")) {
        sessionSequence += 1;
        return result([{ id: `session-${sessionSequence}` }]);
      }
      return result([]);
    });

    const store = new AuthStore(pool);
    const firstLogin = await store.login(account.email, password);
    expect("challenge" in firstLogin).toBe(true);
    expect("tokens" in firstLogin).toBe(false);
    if (!("challenge" in firstLogin)) throw new Error("Expected a TOTP challenge");

    for (let attempt = 0; attempt < 6; attempt += 1) {
      await expect(store.loginWithTotp(firstLogin.challenge.challengeId, "invalid")).resolves.toEqual({
        error: "Invalid credentials",
      });
    }

    const secondLogin = await store.login(account.email, password);
    if (!("challenge" in secondLogin)) throw new Error("Expected a second TOTP challenge");
    const step = Math.floor(Date.now() / 30_000);
    const code = generateCode(base32Decode(secret), step);
    const completed = await store.loginWithTotp(secondLogin.challenge.challengeId, code);
    expect("tokens" in completed).toBe(true);

    const thirdLogin = await store.login(account.email, password);
    if (!("challenge" in thirdLogin)) throw new Error("Expected a third TOTP challenge");
    await expect(store.loginWithTotp(thirdLogin.challenge.challengeId, code)).resolves.toEqual({
      error: "Invalid credentials",
    });
  });
});