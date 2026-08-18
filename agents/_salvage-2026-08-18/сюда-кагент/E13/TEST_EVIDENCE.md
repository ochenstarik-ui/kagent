# E13 — Test Evidence

## Local

- `python -m pytest tests/unit -q`: 137 passed, 2 warnings до CI repair.
- Canonical CI command после repair: 164 passed, 3 warnings.
- Focused E13 closure: 15 passed.
- Changed repair test: 4 passed.
- Ruff changed tests, ROADMAP guard, drift, repository validation, workflow parse и diff check: PASS.

## Git lease fixture

```text
two_updates_one_branch=PASS
stale_lease_rejected=PASS
branch_count=1
```

## Review snapshots

- Initial SHA-256: `d2f49640f355a758220ad2406038116188eb72975f7df76490226a7800018c71`; APPROVE.
- Repair SHA-256: `683a139adbdf460607d894f532f5a4e9e70a3295da0dcf91f9ee8ebdc0e3f0d4`; APPROVE, P0/P1/P2 none.

## CI and merge

- Failed diagnostic run: https://github.com/ochenstarik-ui/kagent/actions/runs/31674226928
- Causal error: `ModuleNotFoundError: No module named 'yaml'`.
- Green repair PR run: https://github.com/ochenstarik-ui/kagent/actions/runs/31674839499
- PR: https://github.com/ochenstarik-ui/kagent/pull/30
- Merge commit: `5537491a9337520570238019bc194d94f3e88460`.

## Two-main-run publication proof

1. https://github.com/ochenstarik-ui/kagent/actions/runs/31676505665
   - source `5537491a9337520570238019bc194d94f3e88460`
   - state `07406e5f6ff0c5f206a7f4709470ef03cb3c55b7`
2. https://github.com/ochenstarik-ui/kagent/actions/runs/31678028569
   - source `a307ea5990a465edbb295db3372924c98e48bddc`
   - state `15595104b70c59039ad43291ab782777dd35f804`

Final remote assertions:

```text
verification-state branch count = 1
automation/verification-state-* branch count = 0
open automation verification PR count = 0
state OID changed across main runs = true
```
