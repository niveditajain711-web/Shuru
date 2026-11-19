from typing import Annotated

from pydantic import BaseModel, Field

from app.models.common import DomainLabel, DomainName, NonEmptyText

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
    """A domain with its indicative first-year price. Prices exclude taxes and fees."""

    name: DomainName
    price: float
    renewal_price: float | None = None
    currency: str
