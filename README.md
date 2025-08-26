# AI-Clinical-LLM-Gateway

gRPC gateway that fans out to LLM providers for grading. Start with a dummy adapter, then plug providers.

## Dev quickstart
- Run `make` command to generate Python stubs from `proto/grader.proto`. Change version in [`./Makefile`](./Makefile) if needed for output. 
- Server and provider adapters coming next.
- When new buffs are generated you will need to modify one of the imports. If you run, it will raise an error, change only that import statement nothing else. 