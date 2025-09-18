# gateway/config/settings.py
import sys
from dotenv import load_dotenv
from pydantic.v1 import BaseSettings, Field
import logging

load_dotenv()


class Settings(BaseSettings):
    # Host and Port Details
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(50051, env="PORT")
    ollama_host: str = Field("http://127.0.0.1:11434", env="OLLAMA_HOST")

    # API Keys
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")

    # Model Behaviour
    model_temperature: float = Field(0, env="MODEL_TEMPERATURE")
    instructor_max_retry: int = Field(3, env="INSTRUCTOR_MAX_RETRY")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # TLS fields
    shared_token: str | None = Field(None, env="SHARED_TOKEN")
    tls_enabled: bool = Field(False, env="TLS_ENABLED")
    tls_cert_path: str | None = Field(None, env="TLS_CERT_PATH")
    tls_key_path: str | None = Field(None, env="TLS_KEY_PATH")


try:
    settings = Settings()
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.exception("Settings initialization failed in ./gateway/config/settings.py")
    sys.exit(1)
