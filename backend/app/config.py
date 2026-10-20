"""Runtime settings. Speech is Gnani when GNANI_API_KEY is set, otherwise mock."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gnani_api_key: str = ""
    gnani_base_url: str = "https://api.vachana.ai"
    gnani_tts_model: str = "timbre-v3.0"
    gnani_tts_voice: str = "Shivani"
    gnani_tts_speed: float = 0.92

    # Evon is self-hosted and OpenAI-compatible. Point LLM_BASE_URL at it,
    # or at any other /v1 chat-completions server. Empty disables the LLM.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "evon"
    llm_enabled: str = "auto"  # auto | on | off

    sample_rate: int = 8000

    @property
    def gnani_on(self) -> bool:
        return bool(self.gnani_api_key.strip())

    @property
    def llm_on(self) -> bool:
        mode = (self.llm_enabled or "auto").strip().lower()
        if mode == "off":
            return False
        return bool(self.llm_base_url.strip())


settings = Settings()
