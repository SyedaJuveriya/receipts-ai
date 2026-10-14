
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Receipts AI"
    app_version: str = "0.1.0"
    lyzr_api_key: str = ""
    lyzr_agent_id: str = ""
    lyzr_api_url: str = "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    @property
    def has_lyzr_api_key(self) -> bool:
        return bool(self.lyzr_api_key.strip())


settings = Settings()
