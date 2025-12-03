from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str | None = None
    DB_PORT: str | None = None
    DB_NAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_USER: str | None = None
    HASH_SALT: bytes | None = None
    SECRET_KEY: str = ""
    
    # ============ AI Configuration ============
    # The system uses a cost-optimized approach:
    # 1. Google Gemini Direct (PREFERRED - cheapest option)
    # 2. OpenRouter as fallback (supports 100+ models)
    
    # Google Gemini Direct API (recommended for lowest cost)
    # Get key at: https://makersuite.google.com/app/apikey
    GOOGLE_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"  # Most cost-effective: $0.075/1M input, $0.30/1M output
    
    # Google Cloud Document AI (for OCR of scanned PDFs)
    # Free tier: 1,000 pages/month
    # Setup: https://cloud.google.com/document-ai/docs/setup
    GOOGLE_CLOUD_PROJECT: str | None = None
    DOCUMENT_AI_LOCATION: str = "eu"  # or "us"
    DOCUMENT_AI_PROCESSOR_ID: str | None = None  # Create OCR processor in Cloud Console
    
    # OpenRouter API (fallback, supports many models)
    # Get key at: https://openrouter.ai/keys
    OPENROUTER_API_KEY: str | None = None
    AI_MODEL: str = "google/gemini-flash-1.5"  # OpenRouter model ID
    # Other options: "openai/gpt-4o-mini", "anthropic/claude-3-haiku", "meta-llama/llama-3.1-8b-instruct"
    
    # ============ Cost Optimization Settings ============
    # Maximum characters to process per API call (reduces costs)
    MAX_TEXT_LENGTH: int = 30000  # ~7,500 tokens
    
    # Cache TTL settings (in seconds)
    CACHE_TTL_SUMMARY: int = 86400  # 24 hours for summaries
    CACHE_TTL_QUIZ: int = 3600      # 1 hour for quizzes
    CACHE_TTL_FLASHCARDS: int = 3600  # 1 hour for flashcards
    
    UPLOAD_DIR: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

