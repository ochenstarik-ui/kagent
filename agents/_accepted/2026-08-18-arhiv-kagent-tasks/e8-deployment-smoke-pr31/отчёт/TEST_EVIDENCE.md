# E8 test and CI evidence

## Independent reviews

- Final E8 snapshot: APPROVE; P0/P1/P2 blockers absent.
- Final ancestry integration after Gateway runtime prerequisites: APPROVE.
- Gateway healthcheck-client prerequisite PR #32: APPROVE, merged and green.
- Gateway ConnectInfo prerequisite PR #33: APPROVE, merged and green.

## Local final integrated verification

```text
Gateway prerequisite contracts: PASS
Raw integration credential coherence: PASS
Focused E8 + Gateway tests: 13 passed
Canonical Python suites: 183 passed, 3 warnings
Ruff: PASS
cargo fmt: PASS
cargo clippy --all-targets -D warnings: PASS
ROADMAP: PASS
Repository validation: PASS
Workflow graph/YAML: PASS
git diff --check: PASS
```

Local `cargo test` was unavailable because Windows lacked `dlltool.exe`; exact Linux PR and main runs passed the real Rust test job.

## Exact green PR evidence

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31687759474

```text
event: pull_request
head: 9513793360c1474bfeb80cb4b86498060d96d295
conclusion: success
deployment: success
seven image builds: success
```

Runtime evidence:

```text
register: HTTP 201
login: HTTP 200
project create: HTTP 201
task create: HTTP 201
task read: HTTP 200
audit read: HTTP 200
Runtime without service secret: HTTP 401
Gateway container: healthy
internal application ports: closed
existing PostgreSQL volume: preserved
new initdb migration: not applied
observability aggregate: degraded (actual finding recorded)
```

## Intentional-red perimeter evidence

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31688253112

```text
event: push
head: 807c75113843848c6f7acfad8efd8ad3b8e9f11a
conclusion: failure

Python perimeter contract:
FAILED test_compose_does_not_publish_internal_service_ports
182 other tests passed

Runtime perimeter guard:
ValueError: internal service control-plane publishes a host port
```

## Post-merge main evidence

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31688669359

```text
event: push
head: 0940d3067d30ed028f26af2577b00a55792ec5b4
conclusion: success
deployment scenario: success
seven image builds: success
all required jobs: success or policy-skipped
verification-state: cc90d632d731d46915a37945208443f35a97d322
```

Post-merge artifact validation:

```text
scenario.json: non-empty and schema-valid
migration.json: non-empty and exact expected values
perimeter.json: five internal services closed
compose-ps.txt: non-empty, Gateway healthy
compose.redacted.log: non-empty, scenario status codes and Runtime 401 present
secret-pattern scan of delivery log: PASS
```
