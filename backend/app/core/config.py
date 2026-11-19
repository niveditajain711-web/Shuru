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
    # these calls cannot spend money.
    gddy_read_base_url: str = "https://api.godaddy.com/v3/domains"
    # Base URL for the quote and the registration. A quote token only works where it was issued, so both
    # use this one. Only `POST /registrations` here can spend money, and not while `demo_mode` is on.
    gddy_purchase_base_url: str = "https://api.godaddy.com/v3/domains"
    gddy_timeout_seconds: float = 15.0

    # While on, the purchase flow runs for real up to the registration: it asks GoDaddy for a quote (free)
    # but never calls `POST /registrations`, so nothing is registered or charged. It defaults to on so that
    # real purchases need an explicit `SHURU_DEMO_MODE=false`.
    demo_mode: bool = True
    # How long a purchase waits for GoDaddy to finish the registration before telling the user it is pending.
    purchase_poll_seconds: float = 30.0
    purchase_poll_interval_seconds: float = 2.0

    regeneration_cap: int = 3

    # New runs per client per window. Each run costs a Claude call, so this protects the Claude spend
    # and the GoDaddy quota on the public site. Keyed by client IP (Caddy forwards it; see architecture 10).
    run_rate_limit: int = 10
    run_rate_window_seconds: float = 3600.0

    # Contact form mail. The mailbox is a GoDaddy Titan mailbox, which needs GoDaddy's SMTP server
    # (`smtpout.secureserver.net`), not `smtp.titan.email`. The username is the full email address.
    # The password comes only from the environment (`SHURU_SMTP_PASSWORD`, in the gitignored `.env`
    # locally and in a secret on the server); it is never in code.
    smtp_host: str = "smtpout.secureserver.net"
    smtp_port: int = 465  # 465 = implicit TLS; any other port uses STARTTLS (e.g. 587)
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_timeout_seconds: float = 15.0
    contact_to: str = ""  # where messages go; defaults to smtp_user
    contact_rate_limit: int = 5  # messages per client per window
    contact_rate_window_seconds: float = 3600.0
