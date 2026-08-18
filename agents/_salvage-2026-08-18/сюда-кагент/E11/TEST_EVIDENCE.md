# E11 Test Evidence

## Exact artifact identity

- Commit and PR head: `f195fcde51830110c013066394b08bef91fbd178`
- Green PR run head: `f195fcde51830110c013066394b08bef91fbd178`
- Cached run head: `f195fcde51830110c013066394b08bef91fbd178`
- Intentional-red proof head: `ef7b291c3e1e92d3247cb50c5874cd68dfb65dbc` (separate deleted proof branch)

## Local deterministic checks

```text
python -m pytest tests/unit/test_image_build_gate.py -q
6 passed

python -m pytest tests/unit -q
139 passed, 2 warnings

ruff check services scripts tests
All checks passed!

python scripts/validate_repository.py
Repository validation passed: 9 required files present

python scripts/drift_check.py
DRIFT CHECK PASSED

python scripts/roadmap_status.py --check --no-run-commands
ROADMAP CHECK PASSED

workflow YAML parser
workflow_yaml_parse=PASS

git diff --check
PASS
```

## Green 7/7 image build

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513

| Image | Result | Job |
|---|---|---|
| gateway | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891140 |
| control-plane | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891270 |
| reasoning-engine | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891090 |
| agent-runtime | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891115 |
| pipeline | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891206 |
| observability | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891324 |
| web | success | https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513/job/94229891165 |

## Intentional-red proof

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31631233995

The temporary proof commit inserted:

```dockerfile
RUN false # E11 intentional red CI proof
```

Observed:

- overall conclusion: `failure`;
- Gateway image build: `failure`;
- all other six image builds: `success`;
- BuildKit failed at the deliberate `RUN false` with exit code 1.

Gateway job: https://github.com/ochenstarik-ui/kagent/actions/runs/31631233995/job/94230222998

## Cached same-SHA run

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31631621926

| Image | First green job duration | Cached job duration |
|---|---:|---:|
| gateway | 128 s | 20 s |
| control-plane | 53 s | 28 s |
| reasoning-engine | 28 s | 20 s |
| agent-runtime | 34 s | 25 s |
| pipeline | 28 s | 14 s |
| observability | 27 s | 16 s |
| web | 128 s | 97 s |

Durations are wall-clock job durations (`completedAt - startedAt`), not only the Docker build step.

## Review evidence

Final staged patch digest:

`084e54dffdf1177aa484134f8ace4ead002e859cfc67fe633d21ab86ac3be841`

Independent verdict: `APPROVE`; P0/P1/P2 blocking findings: none.
