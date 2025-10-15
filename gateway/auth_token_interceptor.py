# gateway/auth_token_interceptor.py
import grpc
from typing import Optional
from gateway.config.settings import settings
from gateway.util.errors import ErrorMessages, TerminalError


class AuthTokenInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, expected_token: Optional[str]):
        if not expected_token.strip():
            raise RuntimeError(ErrorMessages.SET_SHARED_TOKEN)
        self.expected_token = expected_token

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        async def check_token(context):
            if not self.expected_token:
                return
            md = {k: v for k, v in context.invocation_metadata()}
            token = md.get(settings.shared_token_key)
            if token != self.expected_token:
                context.set_trailing_metadata(((settings.error_metadata_key, TerminalError.AUTH_FAILED),))
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    ErrorMessages.AUTH_FAILED,
                )

        if handler.unary_unary:

            async def new_unary_unary(request, context):
                await check_token(context)
                return await handler.unary_unary(request, context)

            return grpc.unary_unary_rpc_method_handler(
                new_unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream:

            async def new_unary_stream(request, context):
                await check_token(context)
                async for resp in handler.unary_stream(request, context):
                    yield resp

            return grpc.unary_stream_rpc_method_handler(
                new_unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.stream_unary:

            async def new_stream_unary(request_iterator, context):
                await check_token(context)
                return await handler.stream_unary(request_iterator, context)

            return grpc.stream_unary_rpc_method_handler(
                new_stream_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.stream_stream:

            async def new_stream_stream(request_iterator, context):
                await check_token(context)
                async for resp in handler.stream_stream(request_iterator, context):
                    yield resp

            return grpc.stream_stream_rpc_method_handler(
                new_stream_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler
