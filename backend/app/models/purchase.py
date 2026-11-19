from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.domain import PremiumFee


class Agreement(BaseModel):
    """A legal agreement the user must accept before buying. Shown as-is from the quote."""

    type: str
    title: str
    url: str | None = None


class Quote(BaseModel):
    """A price locked by GoDaddy for a short time. Prices exclude ICANN fees and taxes. Safe to show the user."""

    domain: str
    period: int
    price: float
    renewal_price: float | None = None
    currency: str
    fees: list[PremiumFee] = []
    agreements: list[Agreement]
    expires_at: datetime
    demo: bool = False


class LockedQuote(Quote):
    """A quote with the secrets needed to buy it. Stored with the run, never sent to the browser
    (the API returns `Quote`; see `schemas.RunResponse`)."""

    token: str
    idempotency_key: str = ""


class Purchase(BaseModel):
    """The outcome of a purchase. In demo mode nothing was registered or charged."""

    domain: str
    status: Literal["pending", "completed"]
    demo: bool
    price: float
    currency: str
    registration_id: str | None = None
    agreed_at: datetime
    expires_at: datetime | None = None
