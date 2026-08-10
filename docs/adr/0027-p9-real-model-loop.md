# ADR-0027: P9 Real Model Loop

## Status
proposed

## Context
We need to merge the P1/P2/P6 implementations into a single pipeline loop and rely on the Reasoning Engine for decision making instead of stubbed outputs. The pipeline also needs rigid error boundaries for provider responses.

## Decision
1. `pipeline.py` integrates directly with the Reasoning Engine for PLAN, DEVELOP and REPAIR.
2. Malformed responses are now hard errors rather than silently falling back to a default value.
3. Failed TEST phase invokes a REPAIR phase followed by another TEST phase until exhaustion.
4. Reasoning request IDs are deterministic based on message content to support replay without breaking cassettes.
