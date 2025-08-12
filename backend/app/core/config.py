import os
import socket
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://127.0.0.1:3000"
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# Optionally append the machine's LAN IP (for dev access from other devices) to allowed origins.
if os.getenv("ADD_LAN_IP_ORIGIN", "true").lower() in ("1", "true", "yes"): 
    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
        # Basic private network check
        if any(lan_ip.startswith(prefix) for prefix in ("192.168.", "10.", "172.16.")):
            lan_origin = f"http://{lan_ip}:3000"
            if lan_origin not in settings.ALLOWED_ORIGINS:  # type: ignore
                settings.ALLOWED_ORIGINS.append(lan_origin)  # type: ignore
    except Exception:
        pass