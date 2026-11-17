from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from `SHURU_*` environment variables or a `.env` file.

    `ANTHROPIC_API_KEY` is not listed here: `load_dotenv()` in `main.py` puts it in the environment,
    where the Anthropic SDK reads it. `GDDY_PAT` is read here (without the `SHURU_` prefix) because we
    send it ourselves as a Bearer token to the GoDaddy REST API. It is a `SecretStr`, so it is not
    shown in logs or reprs.
    """

    model_config = SettingsConfigDict(env_prefix="SHURU_", env_file=".env", extra="ignore", populate_by_name=True)

    log_level: str = "INFO"
    db_path: Path = Path("data/shuru.sqlite")

    brief_model: str = "claude-haiku-5-5"
    site_model: str = "claude-sonnet-5-5"
    brief_max_tokens: int = 2000
    site_max_tokens: int = 8000
    claude_timeout_seconds: float = 60.0

    gddy_pat: SecretStr = Field(default=SecretStr(""), validation_alias="GDDY_PAT")
    # Base URL for the read-only calls (suggest, availability). The GoDaddy test environment is the
    # default. If it returns no suggestions, point this at production (`https://api.godaddy.com/v3/domains`):
    # these calls cannot spend money. Quote and purchase will get their own setting when they are built.
    gddy_read_base_url: str = "https://api.ote-godaddy.com/v3/domains"
    gddy_timeout_seconds: float = 15.0

    regeneration_cap: int = 3
