# Issues and Improvement Backlog (as of 2025-10-15)

## P1. Correctness / Bugs

1) **Potential infinite recursion in `error_mapping.classify_exception`**
   - Code path: when `isinstance(e, httpx.HTTPStatusError)`, it calls `classify_exception(e)` again.
   - Impact: same object → same branch → infinite recursion → stack overflow.
   - Fix: inspect `e.response.status_code` directly and route to status-code handler without re-calling `classify_exception`; or extract message and call `_bad_request/_api_5xx` accordingly.

## P2. Design / Modularity

1) **Provider abstraction leakage in `ChatService`**
   - Temperature handling checks `"gpt-5"` substring; brittle across providers.
   - Consider provider capability flags or per-provider adapters for kwargs.

2) **Error messages coupling**
   - `error_mapping` contains policy flags like `TREAT_RATE_LIMIT_AS_TERMINAL`. Expose via settings to allow environment-level tuning.

3) **Server composition**
   - `server.py` mixes wiring and configuration (interceptors, services). Consider a small `build_server()` factory for better testability.

4) **Docstrings consistency**
   - Several functions have excellent docstrings; others are minimal.
   - Example candidates for improvement: `bind_port`, `_validate_prompts` (parameters, behavior), `_perform_grading` (explicit exceptions).

## P3. DevEx / Tooling

1) **Logging level for third-party libraries**
    - `logging.getLogger("grpc").setLevel(logging.WARNING)` is set; decide if httpx/OpenAI/Anthropic logs should be reduced similarly in production.


## P4. Future Feature

1) **Implement TLS**
    - While not required right now, but TLS should be if backend and gateway live on differnt machines.



## Risk/Sensitive Points by Design
> This application is mostly write once and is independent of how the FASTAPI backend changes. Hence, proto is tight and stict. 
> Currently the Pydantic envelope returns a single `ProblemFeedback`, which maps 1:1 to proto response. If batch is added in proto, remember to update Pydantic + DummyProvider + tests coherently.
> Changing it might be a headache, but I cannot identify any reason for it to change. 
> **For future developers; if needed to change do it carefully. DO NOT TOUCH if you are not aware of what you are doing.**