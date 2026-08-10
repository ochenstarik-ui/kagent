# ADR 0025: Internal Service Perimeter and Shared Secret

## Status
Proposed

## Context

Agent Runtime can execute shell commands, while the default Compose configuration published
its unauthenticated HTTP port on every host interface. Reasoning Engine, Pipeline,
Observability, and Control Plane were published in the same way even though external traffic
is required to terminate at Gateway. Network reachability alone was therefore enough to call
internal action endpoints.

The bootstrap needs a fail-closed control without introducing new dependencies or claiming
the service identity guarantees of mTLS.

## Decision

- The default Compose file publishes only Gateway among KAgent HTTP services. Control Plane,
  Reasoning Engine, Agent Runtime, Pipeline, and Observability remain reachable on the
  internal Compose network. PostgreSQL, NATS, and MinIO keep their loopback-only development
  bindings.
- Service callers send the installation-specific `KAGENT_SERVICE_SECRET` in the
  `X-KAgent-Service-Secret` header. Gateway signs proxied internal requests, and Pipeline
  signs Agent Runtime requests.
- Agent Runtime and Pipeline reject every non-health request with `401` when the header is
  absent or does not match. Comparison is constant-time, and responses and logs never include
  the configured value.
- `/health/live` and `/health/ready` are exempt so container health checks do not depend on
  credentials.
- Gateway exposes Observability under `/api/observability/*`; no Observability host port is
  required.

## Consequences

- A default deployment no longer exposes command execution or internal dashboards directly
  on the host network.
- Every installation must replace the example secret and restart the participating services
  when rotating it. Compose supplies no fixed fallback: an absent or empty value fails closed.
- A single shared secret authenticates membership, not individual service identity. Its
  compromise affects all protected service calls; scoped identities and mTLS remain a later
  security stage.
- No dependency is added; Python uses `secrets.compare_digest`, and Gateway only forwards the
  configured header.
