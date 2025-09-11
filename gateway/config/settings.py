# gateway/config/settings.py
import sys
from dotenv import load_dotenv
from pydantic.v1 import BaseSettings, Field

load_dotenv()


class Settings(BaseSettings):
    host: str = Field("0.0.0.0", env="GATEWAY_HOST")
    port: int = Field(50051, env="GATEWAY_PORT")
    tls_enabled: bool = Field(False, env="GATEWAY_TLS")
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    model_temperature: float = Field(0, env="MODEL_TEMPERATURE")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    ollama_host: str = Field("http://127.0.0.1:11434", env="OLLAMA_HOST")
    instructor_max_retry: int = Field(3, env="INSTRUCTOR_MAX_RETRY")
    # add cert paths later if you enable TLS


try:
    settings = Settings()
except Exception as e:
    print(
        f"❌ Settings initialization failed in ./gateway/config/setting.py: {e}",
        file=sys.stderr,
    )
    sys.exit(1)
