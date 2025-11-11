from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str | None = None
    DB_PORT: str | None = None
    DB_NAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_USER: str | None = None
    HASH_SALT: bytes | None = None
    SECRET_KEY: str = ""
    OPENAI_API_KEY: str | None = None
    UPLOAD_DIR: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
