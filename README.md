# AI Clinical LLM Gateway

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![gRPC](https://img.shields.io/badge/gRPC-async--server-009688?logo=google-cloud&logoColor=white)](https://grpc.io/)
[![Tests](https://github.com/NefariousNiru/AI-Clinical-LLM-Gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/NefariousNiru/AI-Clinical-LLM-Gateway/actions)
[![Lint](https://img.shields.io/badge/Lint-Ruff-black?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)
[![Formatter](https://img.shields.io/badge/Formatter-Black-000000?logo=python&logoColor=white)](https://github.com/psf/black)
[![Tests-Pytest](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Poetry](https://img.shields.io/badge/Poetry-managed-60A5FA?logo=poetry&logoColor=white)](https://python-poetry.org/)

A small, typed gRPC gateway that calls LLM providers (OpenAI, Anthropic, Ollama) or a local Dummy provider and returns schema-validated feedback for a single clinical problem.
This repo favors strict typing, explicit error semantics, and clear separation of concerns.

## Getting started

```bash
# 1) create env and install
poetry install

# 2) Run server.py
python server.py
```


### Visit the docs

All design and operations docs live in the [`docs/`](docs/) folder:

- [Overview](docs/Overview.md)
- [Architecture](docs/Architecture.md)
- [Providers](docs/Providers.md)
- [Error Semantics](docs/Errors.md)
- [Development Guide](docs/Development.md)
- [Proto & Codegen](docs/Protos.md)
- [Operations & Security](docs/Security.md)
- [Testing](docs/Testing.md)
- [FAQ](docs/FAQ.md)
- [Contributing](docs/Contributing.md)

Open issues and suggested improvements are tracked in the project-level [Issues.md](Issues.md).

## Project layout

```
.
├── Dockerfile
├── docs
│   ├── Architecture.md
│   ├── Contributing.md
│   ├── Development.md
│   ├── Errors.md
│   ├── FAQ.md
│   ├── Overview.md
│   ├── Protos.md
│   ├── Providers.md
│   ├── Security.md
│   └── Testing.md
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
├── Issues.md
├── LICENSE.md
├── Makefile
├── Makefile.protos
├── poetry.toml
├── proto
│   └── grader.proto
├── pyproject.toml
├── pytest.ini
├── README.md
├── server.py
└── tests/

```

## Quick tips

- Run `make proto` whenever `proto/grader.proto` changes.
- After codegen, **fix imports** inside generated stubs (see [Proto & Codegen](docs/Protos.md)).
- Prefer raising/propagating `AppError` from `gateway.util.errors` to keep error codes stable.
- Never log prompts or model outputs at INFO; use DEBUG if you must; to maintain privacy.
- Write unit tests for each feature or function you implement in `tests/`
- Abide by code standards and make functions unit-testable
- Run `make` to automatically lint, fix code format and run all tests.

## Links

- Docs index: see [`docs/`](docs/)
- Open issues: [Issues.md](Issues.md)

## License
**Proprietary License — All Rights Reserved**
Copyright (c) 2025
The University of Georgia and Nirupom Bose Roy
