# ADR 0021: TOTP Authentication in Control Plane

## Status
Accepted

## Context
The repository previously had a Python implementation of TOTP (`services/auth/src/totp.py`) which was entirely unintegrated. Integrating it would have required creating a dedicated networked authentication microservice just to calculate a 6-digit code. Since user authentication, JWT management, and user profiles are natively handled by the `control-plane` component written in TypeScript, calling a Python microservice for TOTP verification adds unnecessary latency and network hops in the critical login path.

## Decision
We decided to implement the TOTP second-factor authentication directly within the `control-plane` in TypeScript and delete the unintegrated Python authentication module. 

- We use standard `node:crypto` library to provide `HMAC-SHA1` calculations and constant-time string comparisons required for TOTP (RFC 6238). No external dependencies were added.
- The PostgreSQL schema already included `totp_secret` and `totp_enabled` columns in `accounts`. We enforce constraints using these directly.
- We utilize an in-memory `Map` within the `control-plane` instance to temporarily hold login challenges (acting as pre-auth session states while the user is supplying the 2FA code) and store the last accepted TOTP timestamp to prevent replay attacks, adhering to the requirement of not modifying the database schema. 

## Consequences
- **Positive:** Lower latency on login, fewer network dependencies, and a simplified architecture with one fewer service to deploy.
- **Positive:** Alignment with existing session management capabilities inside the `control-plane`.
- **Negative:** If `control-plane` is scaled out to multiple instances, the in-memory maps for replay protection and login challenges will fail unless sticky sessions are used or we fallback to modifying the database schema to store challenges and last-used steps. For now, this is deemed an acceptable trade-off given the constraints.
