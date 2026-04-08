# tests/test_abort_with_error.py
import pytest
import grpc
from gateway.util.functions import abort_with_error
from gateway.config.settings import settings
from gateway.util.errors import TerminalError, ErrorMessages
from tests.conftest import FakeServicerContext


@pytest.mark.asyncio
async def test_abort_with_error_sets_expected_trailer_and_status():
    ctx = FakeServicerContext()
    with pytest.raises(RuntimeError) as ei:
        await abort_with_error(
            ctx,
            grpc.StatusCode.INVALID_ARGUMENT,
            TerminalError.INVALID_USER_PROMPT,
            ErrorMessages.INVALID_USER_PROMPT,
        )
    trailers = dict(ctx.trailing_metadata)
    assert trailers.get(settings.error_metadata_key) == TerminalError.INVALID_USER_PROMPT
    assert "INVALID_ARGUMENT" in str(ei.value)
