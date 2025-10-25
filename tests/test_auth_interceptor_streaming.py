# tests/test_auth_interceptor_streaming.py
import pytest

from gateway.auth_token_interceptor import AuthTokenInterceptor
from tests.conftest import FakeServicerContext


# Handlers with exactly one shape each, to ensure the interceptor wraps the intended branch


class HandlerUU:
    def __init__(self):
        async def uu(req, ctx):
            return "OK-UU"

        self.unary_unary = uu
        self.unary_stream = None
        self.stream_unary = None
        self.stream_stream = None
        self.request_deserializer = lambda x: x
        self.response_serializer = lambda x: x


class HandlerUS:
    def __init__(self):
        async def us(req, ctx):
            yield "OK-US-1"
            yield "OK-US-2"

        self.unary_unary = None
        self.unary_stream = us
        self.stream_unary = None
        self.stream_stream = None
        self.request_deserializer = lambda x: x
        self.response_serializer = lambda x: x


class HandlerSU:
    def __init__(self):
        async def su(req_iter, ctx):
            return "OK-SU"

        self.unary_unary = None
        self.unary_stream = None
        self.stream_unary = su
        self.stream_stream = None
        self.request_deserializer = lambda x: x
        self.response_serializer = lambda x: x


class HandlerSS:
    def __init__(self):
        async def ss(req_iter, ctx):
            async for _ in req_iter:
                yield "OK-SS"

        self.unary_unary = None
        self.unary_stream = None
        self.stream_unary = None
        self.stream_stream = ss
        self.request_deserializer = lambda x: x
        self.response_serializer = lambda x: x


@pytest.mark.asyncio
async def test_unary_stream_requires_token():
    interceptor = AuthTokenInterceptor("secret")

    async def continuation(_):
        return HandlerUS()

    # success path
    ctx = FakeServicerContext()
    ctx.set_test_metadata(**{"x-gateway-token": "secret"})
    h = await interceptor.intercept_service(continuation, object())
    out = []
    async for item in h.unary_stream(b"req", ctx):
        out.append(item)
    assert out == ["OK-US-1", "OK-US-2"]

    # failure path (wrong token)
    ctx2 = FakeServicerContext()
    ctx2.set_test_metadata(**{"x-gateway-token": "wrong"})
    h2 = await interceptor.intercept_service(continuation, object())
    with pytest.raises(RuntimeError):
        async for _ in h2.unary_stream(b"req", ctx2):
            pass


@pytest.mark.asyncio
async def test_stream_unary_requires_token():
    interceptor = AuthTokenInterceptor("secret")

    async def continuation(_):
        return HandlerSU()

    async def gen():
        yield b"r1"

    # success
    ctx = FakeServicerContext()
    ctx.set_test_metadata(**{"x-gateway-token": "secret"})
    h = await interceptor.intercept_service(continuation, object())
    assert await h.stream_unary(gen(), ctx) == "OK-SU"

    # failure
    ctx2 = FakeServicerContext()
    ctx2.set_test_metadata(**{"x-gateway-token": "wrong"})
    h2 = await interceptor.intercept_service(continuation, object())
    with pytest.raises(RuntimeError):
        await h2.stream_unary(gen(), ctx2)


@pytest.mark.asyncio
async def test_stream_stream_requires_token():
    interceptor = AuthTokenInterceptor("secret")

    async def continuation(_):
        return HandlerSS()

    async def gen():
        yield b"r1"
        yield b"r2"

    # success
    ctx = FakeServicerContext()
    ctx.set_test_metadata(**{"x-gateway-token": "secret"})
    h = await interceptor.intercept_service(continuation, object())
    out = []
    async for item in h.stream_stream(gen(), ctx):
        out.append(item)
    assert out == ["OK-SS", "OK-SS"]

    # failure
    ctx2 = FakeServicerContext()
    ctx2.set_test_metadata(**{"x-gateway-token": "nope"})
    h2 = await interceptor.intercept_service(continuation, object())
    with pytest.raises(RuntimeError):
        async for _ in h2.stream_stream(gen(), ctx2):
            pass
