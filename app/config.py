from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str | None = None
    DB_PORT: str | None = None
    DB_NAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_USER: str | None = None

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
