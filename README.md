# AI-Clinical-LLM-Gateway

gRPC gateway that fans out to LLM providers for grading. Start with a dummy adapter, then plug providers.

## Dev quickstart
- `make proto` to generate Python stubs from `proto/grader.proto`.
- Server and provider adapters coming next.
