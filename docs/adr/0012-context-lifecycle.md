# ADR-0012: Context lifecycle and anchors

- Status: proposed
- Date: 2026-08-03

## Context

The Context Builder assembles a role-specific package with a declared token size and checksum, and the platform forbids loading the whole project memory automatically.

That covers assembly. It does not cover evolution. A task contract permits up to eighty agent turns; over that span the working context grows with tool output, test logs, diffs and retrieved documents. Two failures follow.

The first is drift: as history is truncated or summarised, the original objective, the allowed paths and the Definition of Done lose weight relative to recent noise, and the agent starts solving a different problem than the one it was given.

The second is contamination: content retrieved from repositories, web pages and issue trackers enters the same channel as instructions. The Input Firewall classifies inputs at the boundary; nothing keeps the separation once the content is inside the context window.

## Decision

Context has an explicit lifecycle with declared invariants.

**Token budget per role.** Each role declares a context budget. Exceeding it triggers compaction, never silent truncation.

**Anchors.** A set of elements is never summarised, never dropped and is re-asserted after every compaction: the task contract, allowed and forbidden paths, the Definition of Done, active approvals, and the applicable safety policy. Anchors are re-emitted verbatim at the end of the assembled context.

**Compaction policy.** Compaction summarises the oldest non-anchor material into a structured digest with links to the full artifacts, records the compaction as a run event, and stores the pre-compaction state as a checkpoint artifact. Summaries are labelled as summaries and carry the identifiers of the material they replace.

**Compaction mechanics.** Compaction triggers when context tokens exceed the context window minus a declared reserve, and may also be requested explicitly with focusing instructions that are persisted on the resulting entry. The cut point is found by walking backwards from the newest material until a declared recent-token budget is reached, and it lands on a turn boundary; when a single turn exceeds the budget the cut lands inside it at an assistant message, which is recorded as a split turn. Repeated compaction summarises from the previous kept boundary rather than from the previous summary, so material that survived one pass is reconsidered in the next. The compaction entry records the identifier of the first kept element and the token count recomputed from the rebuilt context, not from the pre-compaction estimate. File operations and other cumulative effects are tracked across compactions rather than summarised away.

**Provenance labelling.** Every context element carries its origin class: platform instruction, task contract, project memory, tool output, or untrusted external content. Untrusted content is delimited and marked as data. Instructions found inside data-class content are never followed; encountering them is a security event reported to the Security Supervisor.

**Determinism.** Assembly and compaction are deterministic given the same inputs, so that a replayed run reconstructs an identical context.

## Consequences

- Long runs stay anchored to their objective, which reduces scope drift and out-of-contract changes.
- Prompt injection through retrieved content is contained by structure, not only by boundary filtering.
- Compaction adds model cost of its own and must be accounted in the budget ledger.
- Deterministic assembly constrains the design of retrieval: unordered or time-dependent sources must be pinned into the context package.

## Related

- ADR-0004 (cassettes) depends on deterministic context assembly.
- ADR-0011 (human decision contract) resumes from checkpoints produced here.
- Specification section 39.
