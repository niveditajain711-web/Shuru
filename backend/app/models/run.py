from datetime import datetime

from pydantic import BaseModel

from app.models.common import Lang, RunState
from app.models.domain import DomainOffer
from app.models.purchase import LockedQuote, Purchase
from app.models.site import Brief, SiteContent

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
    quote: LockedQuote | None = None
    purchase: Purchase | None = None
    regenerations: int = 0
    created_at: datetime
    updated_at: datetime
