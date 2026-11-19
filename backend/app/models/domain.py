from pydantic import BaseModel

from app.models.common import DomainName


class PremiumFee(BaseModel):
    """A one-time fee on a premium (aftermarket) domain, charged on top of the registration price.

    `value` (minor units) is kept as GoDaddy sent it, because it is echoed back verbatim when the user buys.
    """

    type: str
    currency: str
    value: int
    amount: float


class DomainOffer(BaseModel):
    """A domain with its indicative first-year price. Prices exclude ICANN fees and taxes.

    `fees` lists premium-domain fees, which are charged in addition to `price`. It is empty for ordinary domains.
    """

    name: DomainName
    price: float
    renewal_price: float | None = None
    currency: str
    fees: list[PremiumFee] = []
