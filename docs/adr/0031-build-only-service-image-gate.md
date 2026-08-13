# ADR-0031: Build-only service image gate

- Status: proposed
- Date: 2026-08-13

## Context

Compose syntax validation does not execute Dockerfiles. Service image build defects can
therefore remain undetected while unit and integration jobs are green. A previous gateway
Dockerfile also built a dummy source file solely to populate a dependency cache, creating a
risk that a cached placeholder binary could be shipped instead of the product source.

## Decision

Continuous integration has a dedicated matrix job that builds exactly the seven service
images declared with Compose build definitions: gateway, control-plane, reasoning-engine,
agent-runtime, pipeline, observability, and web. It runs on every workflow trigger.

The job uses BuildKit through `docker/build-push-action`, does not load, run, or publish the
images, and uses a separate GitHub Actions layer-cache scope for each service. Dockerfiles
and the complete repository build context remain BuildKit inputs, so relevant file changes
invalidate affected layers normally.

The capability registry names the image-build job as CI evidence. Measurability consumes
that job result, and verified-status publication requires it to pass. Dockerfiles must not
compile dummy or stub source files before replacing them with real source.

## Consequences

- A broken Dockerfile fails its matrix leg and the overall image-build job.
- Builds reuse dependency and compiler layers without publishing intermediate images.
- The gate proves buildability only; startup and runtime health remain separate deployment
  and end-to-end responsibilities.
- Changing shared build context can invalidate caches for multiple services, favoring
  correctness over maximum cache reuse.