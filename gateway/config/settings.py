"""
file: gateway/config/settings.py

Top Level App-Settings
"""

import logging
import os
import sys
from dotenv import load_dotenv
from pydantic import ValidationError
from pydantic.v1 import BaseSettings, Field

logger = logging.getLogger(__name__)

if os.getenv("APP_ENV", "dev") == "dev":
    load_dotenv()


class Settings(BaseSettings):
    # 1) App
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(50051, env="PORT")
    ollama_host: str = Field("http://127.0.0.1:11434", env="OLLAMA_HOST")
    error_metadata_key: str = "x-error-code"
    shared_token_key: str = "x-gateway-token"
    shared_token: str | None = Field(None, env="SHARED_TOKEN")

    # 2) API Keys
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(None, env="ANTHROPIC_API_KEY")

    # 3) Model Behaviour
    model_temperature: float = Field(0, env="MODEL_TEMPERATURE")
    instructor_max_retry: int = Field(3, env="INSTRUCTOR_MAX_RETRY")
    anthropic_max_tokens: int = Field(5000, env="ANTHROPIC_MAX_TOKENS")

    # 4) Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # 5) TLS
    tls_enabled: bool = Field(False, env="TLS_ENABLED")


try:
    settings = Settings()
except ValidationError as e:
    logger.error("❌ Missing/invalid environment variables:")
    for err in e.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        logger.error(f" - {loc}: {msg}")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Settings initialization failed: {e}")
    sys.exit(1)
