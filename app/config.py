import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://app.narrowtech.in,https://narrowtech.in,https://oryq.ai,https://www.oryq.ai"
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "onboarding@resend.dev"
    FRONTEND_URL: str = "http://localhost:3000"
    JWT_SECRET: str  # REQUIRED — no default. App will fail to start if not set in .env/Render.
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True
    )

settings = Settings()

# Fail fast if JWT_SECRET is missing or too weak — never allow a silent insecure fallback.
if len(settings.JWT_SECRET) < 32:
    raise ValueError(
        "JWT_SECRET is missing or too weak (must be at least 32 characters). "
        "Set a strong random value in your .env file or Render environment variables. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )

# Startup diagnostics — safe to print key lengths only (never print secrets)
logger.info(f"Config loaded — SUPABASE_URL: '{settings.SUPABASE_URL[:40]}...' (len={len(settings.SUPABASE_URL)})")
logger.info(f"Config loaded — SUPABASE_KEY length: {len(settings.SUPABASE_KEY)}")
logger.info(f"Config loaded — GROQ_API_KEY present: {bool(settings.GROQ_API_KEY)}")
logger.info(f"Config loaded — GEMINI_API_KEY present: {bool(settings.GEMINI_API_KEY)}")
logger.info(f"Config loaded — OPENAI_API_KEY present: {bool(settings.OPENAI_API_KEY)}")

if not settings.RESEND_API_KEY:
    logger.warning("RESEND_API_KEY is not configured. Email report sending features will fail.")
else:
    logger.info("RESEND_API_KEY is present.")

# DONE - config.py