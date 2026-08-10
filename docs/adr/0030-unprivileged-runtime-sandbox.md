# ADR 0030: Unprivileged Runtime Sandbox

## Status
Proposed

## Context
Agent capabilities (e.g., executing shell commands) require isolation to prevent unauthorized access to the host system and restrict lateral movement. Privileged containers (e.g., Docker-in-Docker) are insecure and not suitable for multi-tenant environments. A solution is needed that provides strict isolation (namespace-based) while running as an unprivileged process inside the `agent-runtime` container.

## Decision
We will use `bubblewrap` (bwrap) as the isolation mechanism for the Agent Runtime.
- `bwrap` provides unprivileged sandbox environments using Linux user namespaces.
- The `ShellTool` will spawn processes wrapped in `bwrap --unshare-all`, severely restricting capabilities (no network, no IPC, restricted PID space, read-only root file system, and isolated workspace binding).
- A mandatory isolation check is added to the `AgentRuntime` execution path. If `bwrap` is missing, the runtime will fail-fast and reject any tool execution.
- Sensitive environment variables (e.g., secrets) are aggressively dropped prior to executing the tool (`env={}`).

## Consequences
- **Positive:** Tools execute in a tightly constrained sandbox. File system boundaries are strictly enforced. Secrets do not enter the sandbox.
- **Negative:** `bubblewrap` must be present in the execution environment (e.g., in the `agent-runtime` Dockerfile or VM image). User namespace support is required in the host kernel.
