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
    # Optional Timbre voice used only when the reply language is English.
    # Empty keeps GNANI_TTS_VOICE and sends language en-IN.
    gnani_tts_voice_en: str = ""
    gnani_tts_speed: float = 0.92

    # OpenAI-compatible chat. Default host is Groq. Auto mode calls Groq only
    # when LLM_API_KEY is set, so an empty key stays on the deterministic flow.
    # Any other base URL is used as-is (a self-hosted server may omit the key).
    # LLM_ENABLED=off disables the model. Eligibility is never the model's.
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    # llama-3.1-8b-instant was shut down on Groq's free and developer tiers
    # on 2026-08-16. openai/gpt-oss-20b is the fast replacement. A deployed
    # service that still names the old id is retried once onto this model.
    llm_model: str = "openai/gpt-oss-20b"
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
        base = self.llm_base_url.strip()
        if not base:
            return False
        if mode == "on":
            return True
        if "groq.com" in base.lower():
            return bool(self.llm_api_key.strip())
        return True


settings = Settings()
