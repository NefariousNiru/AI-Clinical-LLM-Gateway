# Proto & Codegen

Source: `proto/grader.proto`

Generate stubs:

```bash
make -f Makefile.protos
```

This will generate:
- `gateway/grader/v1/grader_pb2.py`
- `gateway/grader/v1/grader_pb2.pyi`
- `gateway/grader/v1/grader_pb2_grpc.py`

## IMPORTANT: fix imports after codegen

`grpcio-tools` will emit relative imports like:
```python
import grader_pb2 as grader__pb2
```
You **must** change them to the package-qualified form:
```python
import gateway.grader.v1.grader_pb2 as grader__pb2
```
Do this in both `grader_pb2_grpc.py` and any other generated modules that import `grader_pb2`.
