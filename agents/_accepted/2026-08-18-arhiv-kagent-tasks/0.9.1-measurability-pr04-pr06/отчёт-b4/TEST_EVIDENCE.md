# B4 test evidence

## Focused tests

```text
python -m pytest tests/unit/test_drift_check.py -q
.......                                                                  [100%]
7 passed in 0.26s
```

## Ruff

```text
ruff check scripts/drift_check.py tests/unit/test_drift_check.py --select E --ignore E501,E402
All checks passed!
```

## Compile and JSON

```text
Compiling 'scripts/drift_check.py'...
Compiling 'tests/unit/test_drift_check.py'...
JSON parse passed: docs/capabilities.json
```

## Drift run 1

Exit code: 1 (expected because real drift remains).

```text
DRIFT CHECK FAILED
  - packages/contracts/src/reasoning.ts
  - services/auth/src/totp.py
  - services/control-plane/src/db.ts
  - services/nats/src/events.py
  - undocumented env vars: CONTROL_PLANE_HOST, CONTROL_PLANE_URL, DATABASE_URL, GATEWAY_REQUEST_LIMIT_BYTES, KAGENT_GATEWAY_PORT, KAGENT_HTTP_HOST, REASONING_ENGINE_URL
```

## Drift run 2

Exit code: 1 (expected because real drift remains).

```text
DRIFT CHECK FAILED
  - packages/contracts/src/reasoning.ts
  - services/auth/src/totp.py
  - services/control-plane/src/db.ts
  - services/nats/src/events.py
  - undocumented env vars: CONTROL_PLANE_HOST, CONTROL_PLANE_URL, DATABASE_URL, GATEWAY_REQUEST_LIMIT_BYTES, KAGENT_GATEWAY_PORT, KAGENT_HTTP_HOST, REASONING_ENGINE_URL
```

## Determinism

```text
byte_identical=yes
sha256_run1=7da5c0f5ef7aadbee7919fb3cbdcba8333b6fb04161449d6798492fb59e649f7
sha256_run2=7da5c0f5ef7aadbee7919fb3cbdcba8333b6fb04161449d6798492fb59e649f7
listed_false_positives_present=0
unknown_evidence_present=no
```

## GitHub Actions

```text
node    PASS
python  PASS
rust    PASS
```

Run: https://github.com/ochenstarik-ui/kagent/actions/runs/31314517652
