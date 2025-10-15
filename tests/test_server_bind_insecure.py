# tests/test_server_bind_insecure.py
import grpc
from server import bind_port


class DummyLogger:
    def __init__(self):
        self.logs = []

    def info(self, *a, **k):
        self.logs.append(("info", a))

    def error(self, *a, **k):
        self.logs.append(("error", a))

    def exception(self, *a, **k):
        self.logs.append(("exception", a))


def test_bind_insecure_path(monkeypatch):
    monkeypatch.setenv("TLS_ENABLED", "false")
    # no cert env required
    logger = DummyLogger()
    server = grpc.aio.server()
    bind_port(server, logger)
    # should have logged TLS disabled
    assert any("TLS disabled" in msg[0] for lvl, msg in logger.logs if lvl == "info")
