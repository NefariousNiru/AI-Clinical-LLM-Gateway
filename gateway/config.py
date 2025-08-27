from dotenv import load_dotenv
from pydantic import BaseModel
import os

load_dotenv()


class Settings(BaseModel):
    host: str = os.getenv("GATEWAY_HOST", "0.0.0.0")
    port: int = int(os.getenv("GATEWAY_PORT", "50051"))
    timeout_sec: float = float(os.getenv("GATEWAY_TIMEOUT_SEC", "30"))
    tls_enabled: bool = os.getenv("GATEWAY_TLS", "0") == "1"
    # add cert paths later if you enable TLS


settings = Settings()
