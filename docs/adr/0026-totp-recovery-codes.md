# 26. TOTP Recovery Codes

Date: 2026-08-10

## Status

Proposed

## Context

Users who lose access to their TOTP authenticator application need a way to regain access to their account. A standard practice is to generate a set of one-time use recovery codes.

We need to implement recovery codes on top of the existing TOTP implementation, ensuring they are stored securely (hashed), generated with high entropy, and prevent concurrent double-use.

## Decision

1.  **Storage:** Store only the SHA-256 hash of each recovery code in the `recovery_codes` table, not the plaintext.
2.  **Generation:** Generate 10 codes, each with 128 bits of entropy (using `node:crypto.randomBytes(16)` encoded as hex). The plaintext is only returned once upon generation.
3.  **Regeneration & Revocation:** Generating new recovery codes requires verifying the user's password and a valid TOTP code. Doing so atomically revokes (deletes) the old set of codes and inserts the new ones within a database transaction.
4.  **Login Flow:** We reuse the persistent TOTP challenge created during password verification. A new endpoint (`/v1/auth/login/recovery`) allows consuming the challenge using a recovery code instead of a time-based code.
5.  **Double-use Prevention:** When a recovery code is used, it is atomically deleted from the database. The `DELETE ... RETURNING 1` SQL command guarantees that concurrent attempts to use the same code yield exactly one success, rejecting replays.
6.  **Disabling TOTP:** If a user disables TOTP altogether, we also delete any remaining recovery codes associated with the account.

## Consequences

-   **Security:** High-entropy codes and hashing protect against offline cracking if the database is compromised. Atomic deletion prevents race conditions and replay attacks.
-   **User Experience:** Users have a fallback if their 2FA device is lost.
-   **Complexity:** We added a new table and two endpoints.
