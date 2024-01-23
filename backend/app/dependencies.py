from pydantic import BaseSettings
from functools import lru_cache
class AppSettings(BaseSettings):
    api_url: str
    ui_url: str
    secret_key: str
    google_client_id: str
    google_secret_key: str
    iugu_token: str
    iugu_prod: str = None
    admin_email: str
    omie_key: str
    omie_secret: str
    redis_url: str

    class Config:
        env_file = ".env"



@lru_cache()
def get_settings():
    return AppSettings()
