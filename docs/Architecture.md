# Architecture

```
FastAPI ──> gRPC──> server.py (grpc.aio)
                    │
                    ├─ AuthTokenInterceptor (metadata: x-gateway-token)
                    │
                    └─ GraderService.Grade()
                         ├─ validate prompts
                         ├─ ChatService(raw_client = get_provider(name))
                         │     └─ Instructor-enforced chat → FeedbackEnvelope
                         ├─ map Pydantic → Proto messages
                         └─ return GradeResponse
```

## Modules

- `server.py`: bootstraps grpc.aio server, binds secure/insecure port, installs interceptor, graceful shutdown.
- `gateway/service/grader_service.py`: RPC surface; validates input, orchestrates call to ChatService, converts models → protobuf.
- `gateway/service/chat_service.py`: provider-specific call + Instructor JSON schema enforcement, token usage normalization.
- `gateway/providers/provider_registry.py`: returns an SDK client or DummyProvider based on `model_provider`.
- `gateway/util/error_mapping.py`: converts exceptions to `AppError` with stable code/kind/grpc status and minimal leakage.
- `gateway/util/logger.py`: idempotent logger init with colorized console and optional file in dev.
- `gateway/config/settings.py`: env-driven settings via Pydantic `BaseSettings`.
- `gateway/config/pydantic_models.py`: strict models for feedback schema.
- Generated stubs in `gateway/grader/v1/*` from `proto/grader.proto`.


## Rate Limiting
> Since this is an internal service it doesn't throttle requests by design. 
> Make sure to maintain throttling at the FASTAPI Backend (number of concurrent requests) based on hardware resources.