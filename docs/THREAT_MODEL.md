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

## Agent workspace threats (0.9)

| Threat | Control in 0.9 | Remaining work |
|---|---|---|
| Host path disclosure | Opaque workspaceRef in public contracts | Worker boundary tests |
| Cross-task workspace reuse | One active workspace per task | PostgreSQL adapter enforcement |
| Unbounded agent fan-out | maxConcurrentAgents validated at session creation | Distributed lease enforcement |
| Network exfiltration | Default networkAccess is denied | Worker allowlist enforcement |
| Review path traversal | Repository-relative path validation and SQL check | Diff parser integration |
| Completion without evidence | Verifying state required before completed | Evidence attachment gate |
| Arbitrary PTY or browser access | No process execution in 0.9 Control Plane | Sandboxed session service |

## Workspace provisioner threats (0.10)

| Threat | Control in 0.10 | Remaining work |
|---|---|---|
| Stale worker continues after restart | Expiring hash-only lease tokens and monotonic generation | Service identity/mTLS |
| Task payload changes after approval | Canonical immutable contract digest validated by worker | Approval signature |
| Checkout escapes worker root | Safe identifiers, resolved root containment and opaque refs | OS sandbox profile |
| Git prompts or argument injection | Argument arrays, prompt disabled, branch validation and timeouts | Egress proxy |
| Cross-task file access | Contract path scope plus resolved workspace containment | Full shell syscall mediation |
