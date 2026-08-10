# ADR 0021: Service Perimeter

## Status

Accepted

## Context

Internal services (reasoning-engine, agent-runtime, pipeline, observability) were exposing ports to the host interface. This is a security risk as they could be accessed directly without going through the gateway.

## Decision

We decided to close the service perimeter by removing published ports for internal services in docker-compose.yml. 
Additionally, we added a `SERVICE_SECRET` for service-to-service authentication between the gateway and internal services.

## Consequences

Internal services are now only accessible through the gateway or via the internal docker network. The system is more secure.
