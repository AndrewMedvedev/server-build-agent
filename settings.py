from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = ""
    folder_id: str = ""


settings = Settings()
