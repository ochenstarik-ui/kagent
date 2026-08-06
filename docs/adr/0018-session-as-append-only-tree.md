# ADR-0018: Session as an append-only tree

- Status: proposed
- Date: 2026-08-06

## Context

A run is currently conceived as a linear timeline of events. That is sufficient for display and insufficient for the two operations that matter most when an autonomous run goes wrong: returning to the moment before a bad decision, and asking what would have happened had the decision differed.

A linear log also has no natural place for the records a long run produces beyond messages: compaction summaries, branch summaries, child cost attribution, labels, model changes, repository state at a point in time.

Prime Agent stores a session as an append-only log of typed entries forming a tree, and builds the model context by walking a path through it. Navigation to any earlier point, forking a new session from an earlier user message, and summarising an abandoned branch fall out of that structure.

## Decision

A session is an append-only sequence of typed entries that forms a tree. Entries are never mutated or deleted.

**Entry types.** At minimum: session header, message, model change, compaction, branch summary, child usage attribution, label, custom entry, repository state, session state. Every entry carries an identifier, a parent identifier, a timestamp and a schema version.

**Context building.** The context sent to the model is derived by walking the path from the current leaf to the root, applying compaction entries as replacements for the spans they summarise. The context is a function of the tree, never a separately maintained buffer.

**Navigation.** An operator or an agent may move to any entry and continue from there. The abandoned branch is preserved and summarised rather than discarded, and the summary is itself an entry.

**Forking.** A new session may be created from any earlier point, inheriting the path up to that entry. Fork is the supported way to explore an alternative without destroying the original.

**Child attribution.** Cost and token usage of a subagent are attributed to the parent session through explicit attribution entries, so that a parent's total is complete while each child's contribution stays separately visible in the tree.

**Authority.** The authoritative store is PostgreSQL and object storage. A local transcript file is a cache and a debugging aid, never the source of truth. This is the point where the borrowed design must diverge from its origin, which treats session files as authoritative.

**Replay coupling.** Combined with recorded model cassettes, navigation plus fork yields counterfactual analysis: re-run from entry N with a different model, prompt version or policy, at zero provider cost, and compare outcomes on identical prior context.

## Consequences

- Incident analysis gains a concrete procedure: navigate to the entry before the bad action, fork, replay under the changed condition.
- The timeline user interface becomes a tree view, which is more work to build and considerably more useful.
- Storage grows with branches; abandoned branches are summarised and subject to retention policy.
- Deriving context from the tree on every turn costs computation and must be deterministic, which ADR-0012 already requires.

## Related

- ADR-0004 (cassettes) supplies deterministic inputs for forked replay.
- ADR-0006 (budget ledger) consumes child usage attribution.
- ADR-0012 (context lifecycle) defines compaction, whose output is an entry here.
- Specification section 43.
