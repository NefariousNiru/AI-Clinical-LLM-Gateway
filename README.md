# AI-Clinical-LLM-Gateway

Async **gRPC** gateway that turns rubric-based grading requests into structured feedback using pluggable LLM providers. It is meant to be called **only** by your FastAPI backend.

* Service: `grader.v1.Grader/Grade`
* Providers: `dummy`, `openai`, `ollama` (more can be added later)
* Strict JSON → Pydantic via **Instructor**
* Simple **shared-token auth** via gRPC metadata (`x-gateway-token`)
* Rotating logs to `logs/app.log` (50 MB, keep 5)
* **No health endpoint** (by design, keep it simple)

---

## Repo layout

```
gateway/
  auth_token_interceptor.py      # shared-token check (x-gateway-token)
  config/
    pydantic_models.py           # FeedbackEnvelope / ProblemFeedback models
    settings.py                  # env-driven configuration (loads .env)
  grader/v1/
    grader.proto                 # API definition (source)
    grader_pb2*.py               # generated stubs (do not edit)
  providers/
    dummy_provider.py            # echo provider for tests
    provider.py                  # Instructor-based provider wrapper
  service/
    grader_service.py            # gRPC implementation + error mapping
  util/
    errors.py, functions.py      # helpers
  server.py                      # entrypoint, logging, TLS bind, auth
proto/
  grader.proto                   # source used by Makefile for codegen
logs/                            # created at runtime (rotation)
```

---

## Requirements & setup (Poetry only)

This project is managed with **Poetry** (no `pip install`).

```bash
# Use your Python 3.12
poetry env use python3.12

# Install all deps from pyproject.toml
poetry install
```

### Environment loading

`gateway/config/settings.py` calls `load_dotenv()` on import.
That means a `.env` file in your **current working directory** (repo root) is automatically loaded—no need to `export` anything when using `poetry run`. If you run the app from somewhere else, make sure `.env` is present in that working dir or switch to absolute env vars.

Create `.env` (example):

```dotenv
# Host and Port Details
HOST=0.0.0.0
PORT=50051
OLLAMA_HOST=http://127.0.0.1:11434

# API Keys
OPENAI_API_KEY=

# Model Behaviour
MODEL_TEMPERATURE=0
INSTRUCTOR_MAX_RETRY=2

# Logging
LOG_LEVEL=INFO

# Security (required for real calls)
SHARED_TOKEN=supersecret

# TLS (local dev: usually leave disabled)
TLS_ENABLED=False
TLS_CERT_PATH=
TLS_KEY_PATH=
```

---

## Running (local, simple)

```bash
poetry run python -m gateway.server
```

What happens:

* Logs to `logs/app.log` (rotates at 50 MB, keeps 5 backups) and to console.
* If `TLS_ENABLED=False`, the server listens insecurely on `HOST:PORT`.
* Calls are accepted only when metadata header `x-gateway-token` matches `SHARED_TOKEN`.

> For local, you can skip TLS. For cross-machine/prod, enable TLS later.

---

## Regenerating protobuf stubs

You already have a `Makefile`. When `proto/grader.proto` changes:

```bash
make
```

When new buffs are generated you will need to modify one of the imports. If you run, it will raise an error, change only that import statement nothing else. 

---

## Configuration (env vars)

These map 1:1 with `gateway/config/settings.py`:

| Name                   | Default                  | Purpose                                                              |
| ---------------------- | ------------------------ |----------------------------------------------------------------------|
| `HOST`                 | `0.0.0.0`                | gRPC bind address                                                    |
| `PORT`                 | `50051`                  | gRPC port                                                            |
| `OLLAMA_HOST`          | `http://127.0.0.1:11434` | Base URL for Ollama (OpenAI-compatible)                              |
| `OPENAI_API_KEY`       | *empty*                  | Required if `model_provider=openai`                                  |
| `MODEL_TEMPERATURE`    | `0`                      | Temperature where the provider supports it                           |
| `INSTRUCTOR_MAX_RETRY` | `3`                      | Instructor’s internal retry budget for schema parsing                |
| `LOG_LEVEL`            | `INFO`                   | `DEBUG`/`INFO`/`WARNING`/`ERROR`                                     |
| `SHARED_TOKEN`         | *empty*                  | Shared secret; Hard to guess. FastAPI must send as `x-gateway-token` |
| `TLS_ENABLED`          | `False`                  | Turn on TLS (optional; skip for local)                               |
| `TLS_CERT_PATH`        | *empty*                  | Server cert PEM when TLS is enabled                                  |
| `TLS_KEY_PATH`         | *empty*                  | Server key PEM when TLS is enabled                                   |

---

## Security (simple)

* **Auth:** Your FastAPI client must include metadata `x-gateway-token: <SHARED_TOKEN>` on every call.
  Missing/mismatch → `UNAUTHENTICATED` (`auth_failed`).
* **TLS:** Deferred for now. When you enable it, set `TLS_ENABLED=True` and provide `TLS_CERT_PATH` / `TLS_KEY_PATH` (PEM files). The content is encrypted in transit; token is protected.

---

## gRPC API

### Service

`grader.v1.Grader/Grade`

### Request fields (what each is for)

* `repeated google.protobuf.Struct rubrics`
  Open JSON describing the grading rubric(s). Required (non-empty). Used to build the LLM prompt.
* `repeated google.protobuf.Struct payload`
  Open JSON describing the problems to grade (inputs). Required (non-empty).
  **Cardinality rule:** the response will contain exactly one `ProblemFeedback` per payload item, in the same order.
* `string system_prompt`
  The system instruction for the LLM (behavior, constraints, style).
* `string user_prompt_template`
  A format string used to render the actual user message. It **must** contain `{rubrics_json}` and `{problems_json}`, which are substituted with pretty-printed JSON.
* `string model_provider`
  One of: `dummy`, `openai`, `ollama`.
* `string model_name`
  Provider-specific model id (e.g., `gpt-4o`, `gpt-5-*`, `llama3:8b`). For `dummy`, any string is accepted.
* `string trace_id` (optional)
  Correlation id for logs and distributed tracing.
* `string job_id` (optional)
  Business id for your backend’s job record (useful for idempotency/status pages).

### Response fields

* `repeated ProblemFeedback feedback`
  Same length and order as `payload`. Each item has:

  * `name` (string)
  * `is_priority` (bool)
  * `identification` / `explanation` / `plan_recommendation` / `monitoring` — each is a `FeedbackSection` with `score`, `evaluation`, `feedback` (strings)
* `string model_provider`
  Echoes the provider used.
* `string model_name`
  Echoes the model actually used.

### Error semantics

* gRPC **status code** indicates class of error:
  `INVALID_ARGUMENT`, `UNAUTHENTICATED`, `UNAVAILABLE`, `DEADLINE_EXCEEDED`
* Trailer metadata `x-error-code` is a machine-readable string:

Transient:

* `network_error`, `provider_timeout`, `rate_limited`, `schema_mismatch`

Terminal:

* `invalid_rubric`, `unsupported_model`, `auth_failed`, `invalid_payload`

Common cases:

* `INVALID_ARGUMENT + schema_mismatch` → LLM output failed schema/cardinality checks.
* `UNAUTHENTICATED + auth_failed` → shared token missing/wrong.
* `UNAVAILABLE + network_error` → provider/network hiccup.

---

## Providers

* **dummy** — returns structured echoes; great for plumbing and schema tests.
* **openai** — requires `OPENAI_API_KEY`; set an appropriate `model_name`.
* **ollama** — expects an OpenAI-compatible endpoint at `OLLAMA_HOST`; set `model_name` to a local model id.

> Adding more (Anthropic, Google, etc.) is straightforward: implement a new adapter that returns a `FeedbackEnvelope` and plug it into `get_provider`.

---

## Logging

* **File:** `logs/app.log` (rotates at 50 MB, 5 backups)
* **Console:** mirrored to stdout
* We avoid logging full prompts/model outputs at INFO; use `LOG_LEVEL=DEBUG` only in dev.

---

## TODO

* Enable TLS when you move beyond local.
* Add more providers (Anthropic, Google, …) behind the same schema.
* Integrate Docker later for easy deployment (mount certs; reuse the same envs).
