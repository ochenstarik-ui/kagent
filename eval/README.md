# Replay evaluation cases

The suite contains exactly three small, self-contained Python standard-library projects. Run
it with:

```bash
python scripts/eval_suite.py --replay
```

Replay is measurement only. It always writes `eval/reports/latest.json`, reports the current
score honestly, and does not gate a release (`gate_passed` remains `false`).

## Runnable case contract (version 1)

Each `eval/cases/<id>/` directory contains:

- `base.tar.gz` — the untouched repository snapshot;
- `contract.json` — task text, category, acceptance argv arrays, immutable verifier path,
  adjacent behavior, and expected artifact paths;
- `cassette.json` — the tracked recorded request/response. The response is a list of bounded
  `write` operations; replay never falls through to a provider. Recorded repair cycles and
  cost are metrics of the recorded response;
- `verifier.py` — an immutable, case-owned acceptance oracle outside the candidate snapshot;
- `mutation.json` — a declared mutation that breaks adjacent behavior while retaining the
  target change.

A case passes only when all four statements are true:

1. acceptance rejects the untouched snapshot (empty diff);
2. applying the recorded response produces every expected artifact;
3. public acceptance and the case-owned verifier accept the replayed result;
4. acceptance rejects the declared mutation applied to a copy of that result.

The case verifier is intentionally outside the candidate repository, so replacing or deleting
candidate tests cannot be the only way to satisfy acceptance. Public tests still run and show
the exercise locally.

## Snapshot format and safety

Snapshots are deterministic POSIX pax tar streams wrapped in gzip. Members are sorted; tar
mtime, uid, gid, uname, and gname are fixed; gzip mtime and filename are empty/fixed. They
contain only regular files from a tiny repository and require no dependency installation.
The runner rejects absolute paths, `..`, links, devices, unsupported member types, invalid
archives, and more than 1,000,000 extracted bytes. It copies members itself instead of using
`extractall`.

To reproduce an archive, create the same sorted UTF-8 file map and use tar metadata
`mtime=uid=gid=0`, mode `0644`, empty owner names, then gzip it with `mtime=0` and an empty
stored filename. The archive itself is the complete candidate repository; cassettes and
verifiers remain case-owned inputs.

## Offline replay guarantee

Replay contains no provider adapter or external-provider code path. Every subprocess receives
a copy of the current environment with known provider-name variables removed. The report
therefore records `provider_calls=0` and `tokens_spent=0`; cost is historical recorded cost
from the cassette, not replay spend.

This is environment scrubbing, **not a network sandbox**. The runner does not claim OS-level
network isolation. The tracked snapshot, commands, verifier, and cassette use only the Python
standard library and make no network calls. A future live or hostile-candidate mode would need
a real sandbox to make a stronger guarantee.

## Cases

- `bugfix_leaky_limiter`: the first request was not counted; client independence is adjacent.
- `feature_add_endpoint`: adds `/health/ready` plus its public test; liveness and 404 behavior
  are checked by the immutable verifier.
- `security_fix_header`: adds `X-Content-Type-Options: nosniff` plus a public test; custom
  headers and status behavior are adjacent.
