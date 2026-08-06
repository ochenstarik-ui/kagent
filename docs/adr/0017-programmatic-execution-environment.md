# ADR-0017: Programmatic execution environment as the agent tool surface

- Status: proposed
- Date: 2026-08-06

## Context

The current design gives the model a registry of discrete tools: read a file, write a file, run a shell command, and later one entry per capability. Every capability costs a tool definition in the prompt, every intermediate result travels back through the model, and no state survives between calls.

An alternative is in production use in Prime Agent (MIT, TypeScript): the model is given exactly one tool, a persistent interpreter, and every other capability is a function call inside it. File operations, project commands, skills and subagent spawning are code, not separate tools. Variables, imports, parsed data and handles survive across turns and across compaction.

The trade is not subtle. Composition becomes free — filtering a file list, computing over it and passing the result onward is one cell instead of five round trips — and the tool catalogue stops consuming context. In exchange, the entire risk surface collapses into one place: an interpreter executing model-authored code. Prime Agent states plainly that its worker and kernel processes provide lifecycle isolation and are not a security sandbox, and that code runs with the user's own permissions. KAgent cannot adopt that posture: it reaches production servers through the infrastructure bridge.

## Decision

KAgent adopts a programmatic execution environment as the model-facing surface, under a blocking precondition.

**Single model-facing tool.** The default runtime exposes one tool to the model: execution in a persistent kernel. Capabilities are exposed as typed callables inside the kernel rather than as separate tool definitions. Extensions may register additional tools deliberately; the base runtime does not require one per capability.

**Persistent state.** Variables, imports, functions, parsed results and child handles survive between steps, across compaction and across kernel restart through a recorded snapshot reference. Kernel state has a declared size limit, a time to live, and is inspectable from the run timeline. State that survives compaction but that nobody can inspect is not permitted.

**Typed host bridge.** The kernel holds no authoritative state and no credentials. Provider calls, credential access, scheduling, subagent creation, approvals, audit, artifact upload, repository operations, infrastructure operations, secret issuance and lease renewal are performed only through typed host requests, validated against schema, capability grants and policy before execution.

**Kernel invariant.** The in-kernel library is a thin shim. It does not call model providers, does not implement an agent loop and does not own persistence. Violating this invariant reintroduces provider SDKs into agent domain logic, which the architecture forbids.

**Blocking precondition.** The environment is enabled only inside a mandatory sandbox: rootless container or microVM, dedicated UID, PID/mount/network namespaces, seccomp, mandatory access control where available, read-only root filesystem, ephemeral workspace, CPU/RAM/PID/disk limits, scoped secrets and explicit capability grants. Without the sandbox the environment is not enabled in any mode, including local single-node development.

**Shell.** Shell access exists as a bounded facility inside the kernel with the same capability policy, not as an unrestricted escape hatch.

## Consequences

- The tool registry in the agent runtime and the tool contracts in the shared package are replaced by typed in-kernel callables. This is a rewrite of an existing component, not an addition.
- Token cost per turn falls, because capability definitions leave the prompt and intermediate results stop travelling through the model.
- The sandbox stops being a hardening item scheduled for later and becomes a delivery blocker for this component.
- A defect in the sandbox is now a total compromise rather than a partial one; sandbox escape testing becomes a required check.
- Skills gain a natural form: an importable package with a typed API rather than a prose instruction.

## Related

- ADR-0012 (context lifecycle) governs what survives compaction alongside kernel state.
- ADR-0018 (session tree) records kernel snapshot references per entry.
- Specification section 42.
