from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models.common import DomainName, Lang, RunState
from app.models.site import Brief, DomainOffer, SiteContent

# --- Run (persisted by the run store and returned by the API) ---


class Run(BaseModel):
    id: str
    state: RunState
    lang: Lang
    idea: str
    brief: Brief
    domains: list[DomainOffer] = []
    domain: DomainOffer | None = None
    site: SiteContent | None = None
    regenerations: int = 0
    created_at: datetime
    updated_at: datetime


# --- API requests ---


class CreateRunRequest(BaseModel):
    idea: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    lang: Lang


class ChooseDomainRequest(BaseModel):
    domain: DomainName


class GenerateSiteRequest(BaseModel):
    """What the user confirmed on the cost review screen. Must match the chosen domain."""

    domain: DomainName
    price: float
