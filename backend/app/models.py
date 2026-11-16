from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Name ideas and keywords become part of `gddy` arguments, so they are restricted to
# characters that are valid in a domain label.
DOMAIN_LABEL_PATTERN = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
DOMAIN_PATTERN = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"

DomainLabel = Annotated[str, StringConstraints(pattern=DOMAIN_LABEL_PATTERN)]
DomainName = Annotated[str, StringConstraints(pattern=DOMAIN_PATTERN)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Lang(StrEnum):
    EN = "en"
    HI = "hi"


class RunState(StrEnum):
    BRIEFED = "briefed"
    DOMAINS_LISTED = "domains_listed"
    DOMAIN_CHOSEN = "domain_chosen"
    SITE_GENERATED = "site_generated"


# --- Claude output (call 1: brief) ---


class Brief(BaseModel):
    audience: NonEmptyText
    tone: NonEmptyText
    tagline: NonEmptyText
    name_ideas: Annotated[list[DomainLabel], Field(min_length=8, max_length=10)]


# --- Claude output (call 2: site content, generated natively in both languages) ---


class Localized(BaseModel):
    en: NonEmptyText
    hi: NonEmptyText


class Hero(BaseModel):
    headline: Localized
    subheadline: Localized


class Offer(BaseModel):
    heading: Localized
    items: Annotated[list[Localized], Field(min_length=2, max_length=5)]


class About(BaseModel):
    heading: Localized
    body: Localized


class FaqItem(BaseModel):
    question: Localized
    answer: Localized


class Contact(BaseModel):
    heading: Localized
    text: Localized


class SiteContent(BaseModel):
    hero: Hero
    offer: Offer
    about: About
    faq: Annotated[list[FaqItem], Field(min_length=3, max_length=5)]
    contact: Contact


# --- Domains ---


class DomainOffer(BaseModel):
    name: DomainName
    price: float
    currency: str


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
