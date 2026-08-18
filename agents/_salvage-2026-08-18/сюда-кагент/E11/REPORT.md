# E11 — Build-only image gate

## Delivery status

**PR open / independently reviewed / CI verified / not merged.**

- Repository: https://github.com/ochenstarik-ui/kagent
- Branch: `wt/e11-image-build-gate`
- Commit: `f195fcde51830110c013066394b08bef91fbd178`
- Commit trailer: `Task: e11-image-build-gate`
- PR: https://github.com/ochenstarik-ui/kagent/pull/29
- PR state at evidence collection: `OPEN`, merge state `CLEAN`
- Base: `main`

No merge, auto-merge, force-push, image publication, or direct push to `main` was performed.

## Implemented

- Added a build-only GitHub Actions matrix for exactly seven Compose service images:
  `gateway`, `control-plane`, `reasoning-engine`, `agent-runtime`, `pipeline`, `observability`, and `web`.
- Configured BuildKit GitHub Actions caches with isolated per-service scopes.
- Kept builds non-publishing and non-loading with `push: false` and `load: false`.
- Removed the Gateway placeholder `fn main() {}` dependency-cache pattern.
- Made the Control Plane Dockerfile workspace-aware so `@kagent/contracts@workspace:*` resolves.
- Removed the Web Dockerfile dependency on the absent `apps/web/public` directory.
- Added computed capability evidence for `infrastructure.images_build`; no manual verified status was asserted.
- Added ADR, changelogs, roadmap/registry wiring, and six regression tests.

## Change size

Commit stat: **12 files changed, 255 insertions, 12 deletions**.

## Independent review

The final staged snapshot was reviewed read-only. Snapshot digest:

`084e54dffdf1177aa484134f8ace4ead002e859cfc67fe633d21ab86ac3be841`

Verdict: **APPROVE**; no P0, P1, or P2 blocking findings.

## Remote evidence

- Green PR run, exact head SHA: https://github.com/ochenstarik-ui/kagent/actions/runs/31631140513
- Intentional-red proof run: https://github.com/ochenstarik-ui/kagent/actions/runs/31631233995
- Failed Gateway proof job: https://github.com/ochenstarik-ui/kagent/actions/runs/31631233995/job/94230222998
- Cached same-SHA run: https://github.com/ochenstarik-ui/kagent/actions/runs/31631621926

The proof branch inserted `RUN false # E11 intentional red CI proof`. Only the Gateway image-build leg failed; the other six image legs succeeded. The temporary branch was deleted after evidence collection and was never part of PR #29.

## Known notes

GitHub emitted Node.js 20 deprecation notices for several third-party actions and forced them onto Node.js 24. These were warnings, not failures. Updating action major versions is outside E11 scope.
