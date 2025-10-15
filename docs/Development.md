# Development Guide

## Prereqs

- Python 3.12
- Poetry
- `protoc` and `grpcio-tools` for codegen

## Install

```bash
poetry install
```

## Code quality

```bash
make format   # ruff --fix + black
make lint     # ruff + black --check
make test     # pytest -v
```

## Running locally
### Dummy Environment
>Set this in a .env file in dev and in the OS Environment in Prod.
>Never check this into git or share it. 

```
# App Settings
# can be 'prod' or 'dev'
APP_ENV=dev
HOST=0.0.0.0
PORT=50051
OLLAMA_HOST=http://127.0.0.1:11434
SHARED_TOKEN=

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
Server listens on `HOST:PORT` (defaults `0.0.0.0:50051`). When TLS is enabled you **must** set `SHARED_TOKEN` and provide `GATEWAY_TLS_CERT_PATH`/`GATEWAY_TLS_KEY_PATH` (see Security).

## Style

- Keep docstrings concise and actionable. First line imperative; explain *why*, not only *what*.
- Avoid logging prompts or completions at INFO.
- Prefer small pure functions; surface errors via `AppError` not raw exceptions.
