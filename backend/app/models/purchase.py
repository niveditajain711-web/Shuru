from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class Agreement(BaseModel):
    """A legal agreement the user must accept before buying. Shown as-is from the quote."""

    type: str
    title: str
    url: str | None = None


class QuoteFee(BaseModel):
    """A premium-domain fee. `value` (minor units) is kept as quoted, because it is echoed back verbatim."""

    type: str
    currency: str
    value: int
    amount: float


class Quote(BaseModel):
    """A price locked by GoDaddy for a short time. Prices exclude ICANN fees and taxes.

    `token` and `idempotency_key` are never sent to the browser (`exclude=True`); the run store
    saves them explicitly.
    """

    domain: str
    period: int
    price: float
    renewal_price: float | None = None
    currency: str
    fees: list[QuoteFee] = []
    agreements: list[Agreement]
    expires_at: datetime
    demo: bool = False
    token: str = Field(default="", exclude=True)
    idempotency_key: str = Field(default="", exclude=True)


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


class PurchaseRequest(BaseModel):
    """What the user accepted on the checkout screen. Must match the stored quote."""

    agreement_types: Annotated[list[Annotated[str, StringConstraints(min_length=1)]], Field(min_length=1)]
    price: float
    acknowledged_fees: bool = False
