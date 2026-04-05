# Pydantic Settings configuration
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: SecretStr

    db_url: str
    redis_url: str

    OPENAI_API_KEY: SecretStr

    NOTION_API_KEY: SecretStr
    NOTION_DATABASE_ID: str

    # Конфігурація Pydantic для читання з файлу .env
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Глобальний інстанс налаштувань для імпорту в інші модулі
settings = Settings()  # type: ignore
