# ADR-0005: Test oracle integrity

- Status: proposed
- Date: 2026-08-03

## Context

The verification stage requires automated tests to pass, and the Definition of Done requires zero test failures.

Stated that way, the requirement is satisfiable in two ways: by making the code correct, or by making the tests agree with whatever the code does. An autonomous developer agent optimises for the measurable goal, so the second path is not a hypothetical failure mode — it is the expected one. Observed variants are: rewriting an assertion, marking a test skipped or expected-to-fail, wrapping a failing call in a broad exception handler, deleting a failing case, and hard-coding the value the implementation currently produces.

Under the current Definition of Done, deleting the failing test satisfies `test_failures: 0`. The verification signal is therefore controlled by the party being verified.

## Decision

The test oracle is separated from the implementation and protected by policy.

**Separation of authorship.** Tests are derived from the specification during the specification and planning stages, by an agent that does not perform the implementation. Reviewer and Test Agent roles must not be served by the same model configuration as the Developer Agent for the same task.

**Freezing.** Once approved, the test set for a task is read-only for the Developer Agent for the whole implementation and repair cycle. Test files are added to `forbidden_paths` of the implementation task contract.

**Separated diffs.** The change set is split into a code diff and a test diff. They are reviewed under different policies. Any modification of pre-existing tests is an `approval_required` action, at the same level as a production change.

**Prohibited constructions.** The test diff is scanned for suppression patterns: skip and expected-failure markers, empty exception handlers, disabled assertions, reduced comparison strictness, lowered coverage thresholds, and verification bypass flags. A match blocks completion and cannot be waived by the implementing agent.

**Mutation check.** New tests must demonstrate that they can fail. A bounded set of synthetic defects is injected into the changed code; the new tests must detect them. The resulting `mutation_score` is recorded as a Definition of Done metric. Tests that detect nothing are decorative and do not count as verification.

**Escape defect accounting.** Defects discovered after a task was marked complete are attributed to the run that introduced them and to the reviewer configuration that approved it. `escape_defects` is a first-class quality metric of the platform.

## Consequences

- Verification cost rises: mutation runs and dual authorship consume additional model and compute budget. The cost is bounded by limiting mutation to the changed files.
- The pipeline gains a class of legitimate blocking outcomes that only a human can clear, which increases `needs-human-decision` volume early on.
- Definition of Done becomes a statement about detection capability rather than about a green status line.
- Legacy repositories with poor existing tests will initially fail more often; this is a true signal, not a regression.

## Related

- ADR-0009 (branching policy) enforces the split of code and test diffs at the repository level.
- ADR-0016 (computed stage status) prevents the same substitution at the roadmap level.
- Specification section 36.
