# AI‑Clinical LLM Gateway

A lightweight, async gRPC gateway that normalizes access to multiple LLM providers, enforces structured outputs with Pydantic via Instructor, and exposes a single grading endpoint for downstream services. Includes strict error taxonomy, auth via per‑request shared token, and environment‑driven configuration.

```
.
├── Dockerfile
├── gateway
│   ├── auth_token_interceptor.py
│   ├── config
│   │   ├── pydantic_models.py
│   │   └── settings.py
│   ├── grader
│   │   └── v1
│   │       ├── grader_pb2_grpc.py
│   │       ├── grader_pb2.py
│   │       └── grader_pb2.pyi
│   ├── providers
│   │   ├── dummy_provider.py
│   │   └── provider_registry.py
│   ├── service
│   │   ├── chat_service.py
│   │   └── grader_service.py
│   └── util
│       ├── error_mapping.py
│       ├── errors.py
│       └── logger.py
├── LICENSE.md
├── Makefile
├── Makefile.protos
├── poetry.toml
├── proto
│   └── grader.proto  # Proto Buff
├── pyproject.toml
├── pytest.ini
├── README.md
├── server.py
└── tests
```

---

## 1) Architecture overview

```
client (grpc / grpcurl / backend) ──▶ GraderService (async gRPC)
                                      │
                                      ├─▶ ChatService
                                      │    ├─▶ Instructor (Pydantic schema enforcement)
                                      │    └─▶ Provider SDK (OpenAI | Anthropic | Ollama | Dummy)
                                      │
                                      ├─▶ Error mapping (exceptions → AppError → gRPC status + trailer)
                                      └─▶ AuthTokenInterceptor (per‑request shared token)
```

* **Single RPC surface**: `GraderService.Grade` standardizes request/response using `proto/grader.proto`.
* **Strict schema**: Model outputs coerced to `FeedbackEnvelope` and nested `ProblemFeedback` via Instructor.
* **Provider registry**: Pluggable clients by string key: `openai`, `anthropic`, `ollama`, `dummy`.
* **Error taxonomy**: Maps SDKs, HTTP status, and network timeouts to stable `AppError` codes and gRPC statuses.
* **Auth**: Optional shared token in metadata header.
* **Logging**: Colorized console, rotating file logs in dev, leveled via env.

---

## 2) Quick start

### Prerequisites

* Python 3.12
* `poetry` for dependency management
* Optionally Docker

### Install

```bash
poetry install
```

### Configure env

Create `.env` at repo root for local dev:

```
# server
# App Settings
# can be 'prod' or 'dev'
APP_ENV=dev
HOST=0.0.0.0
PORT=50051
OLLAMA_HOST=http://127.0.0.1:11434
SHARED_TOKEN=<shared token between backend and gateway>

# API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Model Behaviour
MODEL_TEMPERATURE=0
INSTRUCTOR_MAX_RETRY=2
ANTHROPIC_MAX_TOKENS=5000

# Logging
LOG_LEVEL=INFO

# TLS
TLS_ENABLED=false
```

> The gateway also embeds two header names: `x-error-code` for trailer error codes and `x-gateway-token` for auth. Override requires code changes. Not modifiable on runtime. See gateway/config/settings.py

### Run the server

```bash
poetry run python server.py
```

You should see: `[LLM Gateway] listening on 0.0.0.0:50051 (TLS disabled)`

### Call with grpcurl

```bash
# without auth header
grpcurl -plaintext localhost:50051 list grader.v1.Grader

# with shared token if configured
grpcurl -H 'x-gateway-token: changeme' -plaintext \
  -d '{
        "system_prompt":"You are a strict grader",
        "user_prompt":"Grade this answer...",
        "model_provider":"dummy",
        "model_name":"n/a",
        "trace_id":"t-1",
        "job_id":"j-1"
      }' \
  localhost:50051 grader.v1.Grader/Grade
```

### Docker

```bash
docker build -t ai-clinical-llm-gateway:local .
# example run without TLS
docker run --rm -p 50051:50051 \
  -e HOST=0.0.0.0 -e PORT=50051 \
  -e TLS_ENABLED=false \
  ai-clinical-llm-gateway:local
```

---

## 3) Protobuf surface

`proto/grader.proto` defines:

* `GradeRequest` fields: `system_prompt`, `user_prompt`, `model_provider`, `model_name`, `trace_id`, `job_id`.
* `GradeResponse` fields: `ProblemFeedback feedback`.
* `ProblemFeedback` includes `identification`, `explanation`, `plan_recommendation`, `monitoring` each as `FeedbackSection { score, evaluation, feedback }`.

> The gateway converts the internal Pydantic model to proto on the wire. Keep both in sync when editing.
> To generate stubs run: 
> `make -f Makefile.protos`

* The import will have to change, run to figure out

**Backwards compat tips**

* Add new optional proto fields with default semantics first.
* Version messages when making breaking changes, e.g. `ProblemFeedbackV2` and dual‑write for a release.

---

## 4) Providers

* `openai`: `AsyncOpenAI(api_key=OPENAI_API_KEY)`
* `anthropic`: `AsyncAnthropic(api_key=ANTHROPIC_API_KEY)`
* `ollama`: `AsyncOpenAI(base_url=OLLAMA_HOST, api_key="ollama")` using OpenAI‑compatible API
* `dummy`: returns a static `ChatServiceResponse` to exercise the stack without calling an LLM

Add a provider:

1. Implement a thin wrapper or reuse an SDK client.
2. Register it in `PROVIDER_REGISTER` with a unique key.
3. Wire provider‑specific kwargs in `ChatService._get_response` if needed.

---

## 5) ChatService behavior

* Uses `instructor.AsyncInstructor` to request structured JSON and parse directly into `FeedbackEnvelope`.
* Retries: Instructor handles up to `INSTRUCTOR_MAX_RETRY` attempts for schema conformance.
* Temperature: omitted for model names containing `gpt-5` as those models ignore temperature per comment.
* Anthropic: requires `max_tokens` by API, pulled from `ANTHROPIC_MAX_TOKENS`.
* Token usage: attempts to normalize `input_tokens` and `output_tokens` from provider usage objects.

Failure modes:

* If `envelope.error == true`, ChatService throws an `AppError` of kind TRANSIENT with code `llm_signaled_error` to allow retry at higher layers.
* All other exceptions are mapped through `classify_exception`.

---

## 6) Error taxonomy and mapping

`gateway/util/errors.py` defines:

* `ErrorKind`: `TERMINAL` vs `TRANSIENT`.
* Terminal codes: `auth_failed`, `unsupported_model`, `unsupported_provider`, `invalid_system_prompt`, `invalid_user_prompt`, `quota_exceeded`, `rate_limited`, `context_too_long`, `unexpected_error`, `invalid_payload`.
* Transient codes: `provider_timeout`, `network_error`, `provider_5xx`, `schema_mismatch`, `llm_signaled_error`.
* Human‑readable `ErrorMessages` mapped per code.

`gateway/util/error_mapping.py` translates exceptions from HTTP status, SDK classes, and generic timeouts into `AppError` with a gRPC `StatusCode` and machine‑readable trailer `x-error-code`.

Guidelines:

* Treat 4xx as terminal except 429 where policy can be tuned via `TREAT_RATE_LIMIT_AS_TERMINAL`.
* Context length and unknown model strings are recognized and mapped to specific terminal codes.

---

## 7) Auth and metadata

* `AuthTokenInterceptor` reads `x-gateway-token` from incoming call metadata and compares with `SHARED_TOKEN`.
* On mismatch or absence, it sets trailer `x-error-code: auth_failed` and aborts with `UNAUTHENTICATED`.
* Interceptor wraps all four handler types: unary‑unary, unary‑stream, stream‑unary, stream‑stream.

Client must send:

```
x-gateway-token: <SHARED_TOKEN>
```
---

## 8) Logging

* Initialized via `gateway/util/logger.init_logger()`.
* Colorized console output for humans, rotating file logs in `logs/app.log` when `APP_ENV=dev`.
* Set `LOG_LEVEL` to `DEBUG` during troubleshooting. gRPC library logs are reduced to `WARNING` by default.

---

## 9) TLS

* `server.bind_port` supports TLS and enforces presence of a shared token when TLS is enabled.
* Configure certificate and key paths and switch `TLS_ENABLED=true`.
* If both are on same machine - TLS is not required
---

## 10) Coding standards and guidelines

* **Type hints are contracts**: keep annotations aligned with actual types. Prefer pydantic model types inside the service layer and proto types only at IO boundaries.
* **No secret leakage**: never log full prompts or provider responses at INFO. Use DEBUG only when redacted or in fully isolated environments.
* **Fail fast on invalid input**: validate prompts up front and abort with `INVALID_ARGUMENT` using `abort_with_error`.
* **Stable error surfaces**: only expose `ErrorMessages` to clients. Keep internal exception strings in `cause` for observability.
* **Header names are API**: changing `x-error-code` or `x-gateway-token` is a breaking change for clients.
* **Provider isolation**: add provider‑specific knobs inside `ChatService._get_response`, not scattered through the codebase.
* **Idempotent logger init**: reuse `init_logger` at process start to avoid duplicate handlers.
* **Lints**: target `ruff` + `black` defaults, and `mypy --strict` in CI. No unused vars, no `Any` leaks, explicit return types.
* **Testing**: Please write unit tests for each feature you develop and run `make` to execute `pytest` and format the code.

---

## 11) Current Issues

1. **TLS cert path settings missing**

* `server.bind_port` references `settings.tls_cert_path` and `settings.tls_key_path` but `Settings` does not define them.
* **Fix**: add to `gateway/config/settings.py`.

```python
class Settings(BaseSettings):
    ...
    tls_enabled: bool = Field(False, env="TLS_ENABLED")
    tls_cert_path: str | None = Field(None, env="GATEWAY_TLS_CERT_PATH")
    tls_key_path: str | None = Field(None, env="GATEWAY_TLS_KEY_PATH")
```

2. **Health Check**
* Provide a `HEALTHCHECK` that pings a lightweight reflection or a custom health RPC.

---

## 12) Testing

### Unit tests

* `error_mapping_test.py`: assert mapping for 400, 401, 404, 429, 5xx, timeouts, SDK classes.
* `chat_service_test.py`: dummy provider returns a valid envelope; Instructor path mocked to return schema.
* `auth_interceptor_test.py`: valid vs invalid vs missing token cases per RPC type.
* `grader_service_test.py`: validates prompt checks, provider selection, and error propagation to gRPC trailers.

### E2E smoke with grpcurl

* Start server with `dummy` provider and run the example call above. Assert response shape.

> Consider `pytest-asyncio` and `grpclib` or `grpc.aio` stubs to hit the service in‑process.

---

## 13) Observability

* Correlate with `trace_id` and `job_id` fields in logs.
* Add structured logging fields at INFO for start and end of model calls with durations, token counts, and provider name.
---

## 14) Deployment

* Containerize with the provided `Dockerfile`.
---

## 15) Security notes

* Do not log user prompts or PHI at INFO level. Redact at DEBUG where necessary.
* Require `SHARED_TOKEN` in all environments except local dev. Prefer mutual TLS or per‑client API keys for production.
* Keep provider API keys in secret stores, not on shared hosts.

---

## 16) Contribution guidelines

* Open a PR with a concise title and clear description of the change.
* Include unit tests and update this README or in‑code docstrings when you change behavior.
* Keep commits small and logically grouped.
* Follow the coding standards above. CI will run lint, type check, and tests.

---

## 17) Troubleshooting

* `UNAUTHENTICATED` with `x-error-code: auth_failed`: check the `x-gateway-token` header and server `SHARED_TOKEN`.
* `INVALID_ARGUMENT` with `invalid_system_prompt` or `invalid_user_prompt`: verify non‑empty strings.
* 5xx or `UNAVAILABLE`: check network egress to the provider, SDK timeouts, and retry policy.
* `context_too_long`: trim prompts or choose a model with larger context.
* `unsupported_model`: verify `model_name` against provider catalog.

---

## 18) Minimal client example

Python async client sketch:

```python
import asyncio
import grpc
from gateway.grader.v1 import grader_pb2, grader_pb2_grpc

async def main():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = grader_pb2_grpc.GraderStub(channel)
        md = (('x-gateway-token', 'changeme'),)
        resp = await stub.Grade(grader_pb2.GradeRequest(
            system_prompt="You are a strict grader",
            user_prompt="Grade this answer...",
            model_provider="dummy",
            model_name="n/a",
            trace_id="t-1",
            job_id="j-1",
        ), metadata=md)
        print(resp)

asyncio.run(main())
```

---

## 19) License

See `LICENSE.md`.
