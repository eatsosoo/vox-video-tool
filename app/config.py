from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_mode: str = "demo"
    data_dir: Path = Path("./data")
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    tts_provider: str = "demo"
    vbee_api_key: str = ""
    vbee_app_id: str = ""
    vbee_voice_code: str = "hn_female_ngochuyen_full_48k-fhg"
    vbee_api_url: str = "https://vbee.vn/api/v1/tts"
    vbee_callback_url: str = "https://example.com/vbee-callback"
    vbee_poll_seconds: float = 2.0
    vbee_timeout_seconds: int = 180
    visual_provider: str = "local"
    flowkit_command: str = ""
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    font_file: str = ""
    background_music: str = ""
    music_volume: float = 0.12
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_demo(self) -> bool:
        return self.app_mode.lower() == "demo"

    def production_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.openai_api_key:
            errors.append("Thiếu OPENAI_API_KEY")
        if self.tts_provider.lower() == "vbee":
            if not self.vbee_api_key:
                errors.append("Thiếu VBEE_API_KEY")
            if not self.vbee_app_id:
                errors.append("Thiếu VBEE_APP_ID")
        if self.visual_provider.lower() == "flowkit" and not self.flowkit_command:
            errors.append("Thiếu FLOWKIT_COMMAND")
        return errors


settings = Settings()
