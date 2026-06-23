import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://oryq.ai,https://www.oryq.ai"
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "onboarding@resend.dev"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True
    )

settings = Settings()

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
