# FAQ

### Why use Instructor?

To parse model output directly into Pydantic models with strong validation, capturing schema mismatches early and consistently.

### Why a dummy provider?

To exercise the entire gRPC and UI flow offline, without network keys or costs.

### How are errors surfaced to clients?

Via gRPC Status (code + message) and a machine-readable `x-error-code` trailer. See `Errors.md`.

### Can I return multiple problems in one request?

Current schema returns a single `ProblemFeedback`. Batch behavior can be added by extending the proto and Pydantic models.
