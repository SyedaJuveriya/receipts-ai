from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Receipts AI"
    app_version: str = "0.1.0"


settings = Settings()
