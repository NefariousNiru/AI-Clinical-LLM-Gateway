# tests/test_auth_token_interceptor.py
import pytest
from gateway.auth_token_interceptor import AuthTokenInterceptor
from tests.conftest import FakeServicerContext


class DummyHandler:
    """Mimic grpc.aio method handler with unary_unary shape."""

    def __init__(self):
        self.request_deserializer = lambda x: x
        self.response_serializer = lambda x: x

        async def fn(request, context):
            return "OK"

        self.unary_unary = fn
        self.unary_stream = None
        self.stream_unary = None
        self.stream_stream = None


@pytest.mark.asyncio
async def test_auth_success(monkeypatch):
    interceptor = AuthTokenInterceptor("secret")

    async def continuation(_details):
        return DummyHandler()

    context = FakeServicerContext()
    context.set_test_metadata(**{"x-gateway-token": "secret"})
    handler = await interceptor.intercept_service(continuation, object())
    resp = await handler.unary_unary(b"req", context)
    assert resp == "OK"
    # no trailers set on success
    assert context.trailing_metadata == ()


@pytest.mark.asyncio
async def test_auth_failure_sets_trailer_and_aborts(monkeypatch):
    interceptor = AuthTokenInterceptor("secret")

    async def continuation(_details):
        return DummyHandler()

    context = FakeServicerContext()
    context.set_test_metadata(**{"x-gateway-token": "wrong"})
    handler = await interceptor.intercept_service(continuation, object())
    with pytest.raises(RuntimeError):
        await handler.unary_unary(b"req", context)
    # trailer should carry x-error-code = auth_failed
    trailers = dict(context.trailing_metadata)
    assert "x-error-code" in trailers
    assert trailers["x-error-code"] == "auth_failed"
