from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from `SHURU_*` environment variables or a `.env` file.

    Secrets (`ANTHROPIC_API_KEY`, `GDDY_PAT`) are not listed here: the Anthropic SDK and the
    `gddy` CLI read them from the environment themselves, so they never pass through our code.
    """

    model_config = SettingsConfigDict(env_prefix="SHURU_", env_file=".env", extra="ignore")

    log_level: str = "INFO"
    db_path: Path = Path("data/shuru.sqlite")

    brief_model: str = "claude-haiku-5-5"
    site_model: str = "claude-sonnet-5-5"
    brief_max_tokens: int = 2000
    site_max_tokens: int = 8000
    claude_timeout_seconds: float = 60.0

    gddy_binary: str = "gddy"
    gddy_env: str = "ote"
    gddy_timeout_seconds: float = 15.0

    regeneration_cap: int = 3
