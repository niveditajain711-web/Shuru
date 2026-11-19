"""The raw JSON of the GoDaddy Domain Lifecycle API (v3), as it arrives on the wire.

Field names follow GoDaddy's camelCase and prices are integers in minor units. Nothing here is
used outside `clients/gddy_client.py`, which converts these into our own models.
"""

from datetime import datetime

from pydantic import BaseModel


class Money(BaseModel):
    currencyCode: str
    value: int


class Fee(BaseModel):
    type: str
    fee: Money


class TermPrice(BaseModel):
    term: str
    period: int
    price: Money
    renewalPrice: Money | None = None
    fees: list[Fee] = []  # premium (aftermarket) domains only


class Suggestion(BaseModel):
    domain: str
    prices: list[TermPrice] = []


class Suggestions(BaseModel):
    items: list[Suggestion]


class Availability(BaseModel):
    domain: str
    available: bool | None = None
    prices: list[TermPrice] = []
    error: dict | None = None


class Availabilities(BaseModel):
    items: list[Availability]


class Agreement(BaseModel):
    agreementType: str
    title: str
    url: str | None = None


class RegistrationQuote(BaseModel):
    """The reply to `POST /registration-quotes`, as the OpenAPI spec defines it (checked against a real reply).

    When `available` is false there is no token. `fees` is present only for premium (aftermarket) domains.
    """

    domain: str
    available: bool
    quoteToken: str | None = None
    expiresAt: datetime | None = None
    period: int | None = None
    price: Money | None = None
    renewalPrice: Money | None = None
    fees: list[Fee] = []
    requiredAgreements: list[Agreement] = []


class Registration(BaseModel):
    registrationId: str
    status: str
    expiresAt: datetime | None = None
