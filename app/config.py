from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_mode: str = "demo"
    data_dir: Path = Path("./data")
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    vbee_api_key: str = ""
    vbee_app_id: str = ""
    vbee_voice_code: str = "hn_female_ngochuyen_full_48k-fhg"
    flowkit_command: str = ""
    ffmpeg_bin: str = "ffmpeg"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

