STAGE-4 IS LOCKED.

This layer is a STRICT, USER-DECLARED ORCHESTRATION LAYER.

It MUST NOT:
- Generate plans
- Modify plans
- Infer parameters
- Retry execution
- Branch or loop
- Call Stage-3 internals
- Add intelligence
- Add defaults

All changes require a new STAGE number.

Violation of this file means Hearth is no longer non-agentic.
