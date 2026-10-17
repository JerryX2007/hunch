from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads values from environment variables or backend/.env (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None  # e.g. postgresql+psycopg://user:pass@host:5432/hunch
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
