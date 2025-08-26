PROTO=proto/grader.proto

.PHONY: proto
proto:
	python -m grpc_tools.protoc -Iproto \
	    --python_out=gateway/grader/v1 \
	    --grpc_python_out=gateway/grader/v1 \
	    $(PROTO)
