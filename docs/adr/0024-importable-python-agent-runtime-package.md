# ADR-0024: Importable Python agent runtime package

- Status: accepted
- Date: 2026-08-10

## Context

The Agent Runtime implementation lived under `services/agent-runtime`. A hyphen is valid in
a filesystem path but not in a Python package name, so the runtime unit test could not import
its production module through the repository package hierarchy. Keeping both spellings or
loading the module by path would create two implementation locations or bypass normal Python
imports.

## Decision

The Agent Runtime filesystem and Python package boundary is
`services/agent_runtime`. Docker build paths, capability metadata and CI evidence use that
same canonical location. No compatibility directory, path-based dynamic import or
`sys.path` adjustment is retained.

The Compose service and network hostname remain `agent-runtime`; only the source package
path changes.

## Consequences

- Runtime code is importable as `services.agent_runtime.src.runtime` from repository-root
  test and tooling commands.
- Docker and capability evidence resolve to the same canonical implementation.
- Any consumer that addressed the old source filesystem path must switch to the underscore
  spelling.
