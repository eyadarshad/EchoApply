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
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_FLASH_MODEL: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash-latest")
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro-latest")

    # API Keys
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "")
    JOOBLE_API_KEY: str = os.getenv("JOOBLE_API_KEY", "")

settings = Settings()
