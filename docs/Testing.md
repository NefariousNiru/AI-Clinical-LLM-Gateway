# Testing

> Always write comprehensive tests for all functionality written. Write functions that are testable.


The suite uses `pytest` and covers:
- Provider registry wiring
- ChatService kwargs and Instructor integration (mocked)
- Error mapping policy
- Auth interceptor behavior (unary and streaming)
- gRPC server bind scenarios
- Pydantic constraints & proto roundtrip

Run:
```bash
pytest -v --maxfail=1 --disable-warnings
# or
make test
```

Add new tests under `tests/` and keep fixtures in `tests/conftest.py` minimal and explicit.
