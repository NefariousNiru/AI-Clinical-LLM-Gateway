# Operations & Security

## Auth

The server installs `AuthTokenInterceptor`, which expects a shared token in request metadata:
- key: `x-gateway-token` (configurable via settings) must reflect on FASTAPI backend if changed
- value: exact match to `SHARED_TOKEN` env var

On mismatch, it sets trailing metadata `x-error-code=auth_failed` and aborts with UNAUTHENTICATED.

### Dev caveat

- `AuthTokenInterceptor` is constructed at server startup with the current `SHARED_TOKEN`. If `SHARED_TOKEN` is missing or empty, initialization will fail. In TLS mode the server also enforces that a token is set.
- In dev mode a shared token is **required**.

## TLS

- If `TLS_ENABLED=true`, provide `GATEWAY_TLS_CERT_PATH` and `GATEWAY_TLS_KEY_PATH`. The server binds with `grpc.ssl_server_credentials`.
- In TLS mode a shared token is **required**.

## Logging

- Level governed by `LOG_LEVEL` env.
- Do not log prompts/responses at INFO; prefer DEBUG if necessary.
- Dev environments write to `logs/app.log`; containers usually rely on stdout.
- Prod env should log at INFO level.