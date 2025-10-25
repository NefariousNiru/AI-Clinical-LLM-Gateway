# Overview

This gateway exposes a single gRPC service (`grader.v1.Grader/Grade`) which validates a request, calls a model provider, enforces a response schema with Pydantic/Instructor, and returns structured feedback for one clinical problem.

Key properties:
- **Strict schema**: Model output is parsed into `FeedbackEnvelope` and `ProblemFeedback` (Pydantic).
- **Provider abstraction**: `provider_registry` returns an SDK client or Dummy provider.
- **Error normalization**: `error_mapping.classify_exception` maps SDK/network errors into stable `AppError` codes and gRPC statuses.
- **Auth**: a simple shared-token interceptor (`AuthTokenInterceptor`) checks metadata for a token before invoking handlers.
- **Observability**: light-weight timing + logging; avoids leaking PHI or prompts in INFO logs.

Terminology:
- **Envelope**: top-level response containing `feedback` and `errors` flag for LLM-signaled failures.
- **Provider**: concrete SDK client (OpenAI/Anthropic/Ollama) or DummyProvider (local/testing).
