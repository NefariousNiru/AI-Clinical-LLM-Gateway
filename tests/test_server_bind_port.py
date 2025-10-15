# tests/test_server_bind_port.py
import pytest
import grpc

from gateway.config.settings import settings
from server import bind_port


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, *a, **k):
        self.messages.append(("info", a))

    def error(self, *a, **k):
        self.messages.append(("error", a))

    def exception(self, *a, **k):
        self.messages.append(("exception", a))


@pytest.mark.skipif(not settings.tls_enabled, reason="TLS disabled")
def test_bind_port_tls_missing_paths(monkeypatch):
    monkeypatch.setenv("TLS_ENABLED", "true")
    logger = DummyLogger()
    server = grpc.aio.server()
    with pytest.raises(SystemExit):
        bind_port(server, logger)  # should exit due to missing cert/key paths
