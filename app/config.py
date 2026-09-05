from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./clinical_cdss.db"
    sql_echo: bool = False
    demo_data: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CDSS_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
