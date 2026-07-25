# Initial Threat Model

## Protected assets

- user credentials and sessions;
- provider API keys;
- source repositories;
- generated code and artifacts;
- task and audit history;
- cluster identities;
- production deployment credentials.

## Trust boundaries

1. Browser or client to Gateway.
2. Gateway to Control Plane.
3. Control Plane to broker, database and object storage.
4. Controller to execution workers.
5. Agent sandbox to host.
6. External model and tool providers.

## Initial threats and controls

| Threat | Initial control |
|---|---|
| Credential disclosure | No tracked secrets; runtime secret injection; planned vault |
| Prompt injection | Untrusted-input classification; capability policy; isolated tools |
| Arbitrary host command execution | No shell in the bootstrap; later allowlisted sandbox tools |
| Cross-project data access | Project-scoped identifiers and authorization checks |
| Event spoofing | Service identity and signed/enveloped events in later increment |
| Audit tampering | Append-only model now; hash chain before production |
| Supply-chain compromise | Lockfiles, license inventory, dependency scanning and SBOM |
| Public exposure of data services | Docker ports bound to loopback |
| Retry storms | Bounded retries, leases and circuit breakers in workflow runtime |
| Artifact replacement | Content hashes and immutable object keys |

## Non-goals of the bootstrap

The bootstrap is not production-ready and does not yet provide:

- user authentication;
- encryption at rest;
- mTLS;
- sandbox execution;
- credential vault;
- hash-chained audit;
- production network policies.

These are explicit blockers for production deployment.
