from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.models import DomainName, Lang


class CreateRunRequest(BaseModel):
    idea: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    lang: Lang


class ChooseDomainRequest(BaseModel):
    domain: DomainName


class GenerateSiteRequest(BaseModel):
    """What the user confirmed on the cost review screen. Must match the chosen domain."""

    domain: DomainName
    price: float


class PurchaseRequest(BaseModel):
    """What the user accepted on the checkout screen. Must match the stored quote."""

    agreement_types: Annotated[list[Annotated[str, StringConstraints(min_length=1)]], Field(min_length=1)]
    price: float
    acknowledged_fees: bool = False
