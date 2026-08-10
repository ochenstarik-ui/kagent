# ADR 0023: TOTP Authentication in Control Plane

## Status
Accepted

## Context
The repository previously had a Python implementation of TOTP (`services/auth/src/totp.py`) which was entirely unintegrated. Integrating it would have required creating a dedicated networked authentication microservice just to calculate a 6-digit code. Since user authentication, JWT management, and user profiles are natively handled by the `control-plane` component written in TypeScript, calling a Python microservice for TOTP verification adds unnecessary latency and network hops in the critical login path.

## Decision
We decided to implement the TOTP second-factor authentication directly within the `control-plane` in TypeScript and delete the unintegrated Python authentication module.

- We use standard `node:crypto` library to provide `HMAC-SHA1` calculations and constant-time string comparisons required for TOTP (RFC 6238). No external dependencies were added.
- The PostgreSQL schema already included `totp_secret` and `totp_enabled` columns in `accounts`. We enforce constraints using these directly.
- We utilize PostgreSQL to store login challenges (acting as pre-auth session states while the user is supplying the 2FA code) in a `totp_challenges` table, and store the last accepted TOTP timestamp directly in the `accounts` table (`totp_last_step`) to prevent replay attacks. This separates the TOTP policy logic from the persistence layer and enables seamless scaling across multiple `control-plane` instances.

## Consequences
- **Positive:** Lower latency on login, fewer network dependencies, and a simplified architecture with one fewer service to deploy.
- **Positive:** Alignment with existing session management capabilities inside the `control-plane`.
- **Positive:** Safely supports cross-instance scaling without requiring sticky sessions, thanks to atomic PostgreSQL storage for challenges and replay markers.
