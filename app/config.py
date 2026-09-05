from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"Boolean value expected, got: {value!r}")


class Settings(BaseSettings):
    database_url: str = "sqlite:///./clinical_cdss.db"
    sql_echo: bool = False
    demo_data: bool = False

    @field_validator("sql_echo", "demo_data", mode="before")
    @classmethod
    def validate_bool_fields(cls, value: Any) -> bool:
        return _parse_bool(value)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CDSS_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
