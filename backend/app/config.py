from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "童心译站 Agent"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    model_provider: Literal["mock", "bailian"] = "mock"
    dashscope_api_key: SecretStr | None = None
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_model: str = "qwen-plus"
    database_url: str | None = None
    app_api_token: SecretStr | None = None
    request_timeout_seconds: float = 30.0
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.app_env not in {"staging", "production"}:
            return self
        if not self.database_url:
            raise ValueError(f"{self.app_env.title()} requires DATABASE_URL")
        if self.app_api_token is None or not self.app_api_token.get_secret_value().strip():
            raise ValueError(f"{self.app_env.title()} requires APP_API_TOKEN")
        if self.app_env == "production":
            if self.model_provider != "bailian":
                raise ValueError("Production requires MODEL_PROVIDER=bailian")
            if (
                self.dashscope_api_key is None
                or not self.dashscope_api_key.get_secret_value().strip()
            ):
                raise ValueError("Production requires DASHSCOPE_API_KEY")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
