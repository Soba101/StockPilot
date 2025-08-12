import os
import socket
from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# Pre-load project root .env (one level above backend/) if running uvicorn from backend dir
try:  # best-effort; silently continue if anything fails
    root_env = Path(__file__).resolve().parents[3] / ".env"
    if root_env.exists():
        load_dotenv(root_env)
except Exception:
    pass

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

    # Chat / LLM settings
    CHAT_ENABLED: bool = bool(int(os.getenv("CHAT_ENABLED", "1")))
    CHAT_LLM_FALLBACK_ENABLED: bool = bool(int(os.getenv("CHAT_LLM_FALLBACK_ENABLED", "0")))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234")
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "openai/gpt-oss-20b")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "3"))

    # Alerting / notifications
    ALERT_CRON_TOKEN: str = os.getenv("ALERT_CRON_TOKEN", "dev-cron-token")
    ALERT_EMAIL_FROM: str = os.getenv("ALERT_EMAIL_FROM", "alerts@stockpilot.local")
    ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")  # optional override
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "25"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    ALERT_WEBHOOK_URL: str = os.getenv("ALERT_WEBHOOK_URL", "")
    ALERT_SIGNING_SECRET: str = os.getenv("ALERT_SIGNING_SECRET", "")
    ALERT_DAILY_HOUR: int = int(os.getenv("ALERT_DAILY_HOUR", "8"))
    
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