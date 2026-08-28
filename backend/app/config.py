import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Settings:
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "3000"))
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # LLMs
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY_RESUME: str = os.getenv("GEMINI_API_KEY_RESUME", os.getenv("GEMINI_API_KEY", ""))
    GEMINI_API_KEY_SEARCH: str = os.getenv("GEMINI_API_KEY_SEARCH", os.getenv("GEMINI_API_KEY", ""))
    GEMINI_API_KEY_GENERAL: str = os.getenv("GEMINI_API_KEY_GENERAL", os.getenv("GEMINI_API_KEY", ""))
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_FLASH_MODEL: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-flash")

    # OpenRouter Fallback Models
    OPENROUTER_MODEL_PRIMARY: str = os.getenv("OPENROUTER_MODEL_PRIMARY", "nvidia/llama-3.1-nemotron-ultra-253b-v1:free")
    OPENROUTER_MODEL_SECONDARY: str = os.getenv("OPENROUTER_MODEL_SECONDARY", "nvidia/llama-3.3-nemotron-super-49b-v1:free")
    OPENROUTER_MODEL_TERTIARY: str = os.getenv("OPENROUTER_MODEL_TERTIARY", "meta-llama/llama-3.3-70b-instruct:free")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Frontend URL (for email templates)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", f"http://localhost:{os.getenv('FRONTEND_PORT', '3000')}")

    # Supabase Auth
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # API Keys
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "")
    JOOBLE_API_KEY: str = os.getenv("JOOBLE_API_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    # Security
    ENCRYPTION_SECRET: str = os.getenv("ENCRYPTION_SECRET", "")

    # Storage — portable data directory for local fallback files
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"))

settings = Settings()

# Ensure data directory exists at import time
os.makedirs(settings.DATA_DIR, exist_ok=True)
