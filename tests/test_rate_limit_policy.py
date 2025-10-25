# tests/test_rate_limit_policy.py
import types
from gateway.util import error_mapping as em
from gateway.util.errors import TerminalError, TransientError, ErrorKind


class _StatusExc(Exception):
    def __init__(self, status_code: int, msg: str = "boom"):
        super().__init__(msg)
        self.status_code = status_code
        self.response = types.SimpleNamespace(status_code=status_code)


def _exc(status, msg="boom"):
    return _StatusExc(status, msg)


def test_429_default_terminal(monkeypatch):
    err = em.classify_exception(_exc(429, "rate limited"))
    assert err.code == TerminalError.RATE_LIMITED
    assert err.kind == ErrorKind.TERMINAL


def test_429_transient_when_flag_false(monkeypatch):
    monkeypatch.setattr(em, "TREAT_RATE_LIMIT_AS_TERMINAL", False)
    err = em.classify_exception(_exc(429, "rate limited"))
    assert err.code == TransientError.NETWORK_ERROR  # per current policy branch
    assert err.kind == ErrorKind.TRANSIENT
