from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    api_key: str = ""
    folder_id: str = ""


settings = Settings()
