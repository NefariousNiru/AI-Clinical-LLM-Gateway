# Error Semantics

All provider/SDK/network exceptions are normalized to `AppError`:

- `kind`: TRANSIENT or TERMINAL (TRANSIENT thrown when you want backend to retry, TERMINAL otherwise.)
- `code`: stable string (e.g., `auth_failed`, `unsupported_model`, `provider_timeout`)
- For each code make sure to add a message in `ErrorMessages`
- `grpc_status`: mapped status code surfaced via gRPC
- `details`: short human-readable text for clients

`GraderService` uses `abort_with_error` to place a machine-readable code in trailing metadata (key: `x-error-code`) and to abort with a corresponding gRPC status and message.

See: `gateway/util/errors.py` (codes + messages) and `gateway/util/error_mapping.py` (classifier).
