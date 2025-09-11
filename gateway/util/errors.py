# gateway/util/errors.py


class TransientError:
    NETWORK_ERROR = "network_error"
    PROVIDER_TIMEOUT = "provider_timeout"
    RATE_LIMITED = "rate_limited"
    SCHEMA_MISMATCH = "schema_mismatch"


class TerminalError:
    INVALID_RUBRIC = "invalid_rubric"
    UNSUPPORTED_MODEL = "unsupported_model"
    AUTH_FAILED = "auth_failed"
    INVALID_PAYLOAD = "invalid_payload"
