from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str | None = None
    DB_PORT: str | None = None
    DB_NAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_USER: str | None = None
    HASH_SALT: bytes | None = None
    SECRET_KEY: str = ""
    
    # AI Configuration - Using OpenRouter for multi-model support
    OPENROUTER_API_KEY: str | None = None
    AI_MODEL: str = "google/gemini-flash-1.5"  # Default to Gemini Flash for cost-effectiveness
    # Alternative models: "openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-pro-1.5"
    GOOGLE_API_KEY: str | None = None  # Add this
    GEMINI_MODEL: str = "gemini-pro" # Or "gemini-1.5-flash" for Gemini direct
    
    UPLOAD_DIR: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
