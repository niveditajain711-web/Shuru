"""Shared test helpers (not fixtures: those live in conftest.py)."""

from datetime import UTC, datetime, timedelta

import httpx

from app.clients.gddy_client import GddyClient
from app.models import Brief, Lang, LockedQuote, SiteContent
from app.schemas import PurchaseRequest

BASE = "https://api.example.test/v3/domains"

NAME_IDEAS = [f"achaar{i}" for i in range(1, 9)]


def make_brief() -> Brief:
    return Brief(audience="Home cooks", tone="Warm", tagline="Pickles like home", name_ideas=NAME_IDEAS)


def localized(text: str) -> dict:
    return {"en": text, "hi": f"{text} (hindi)"}


def make_site() -> SiteContent:
    return SiteContent.model_validate(
        {
            "hero": {"headline": localized("Homemade achaar"), "subheadline": localized("From Lucknow")},
            "offer": {"heading": localized("What we make"), "items": [localized("Mango"), localized("Lemon")]},
            "about": {"heading": localized("About"), "body": localized("A family recipe")},
            "faq": [{"question": localized(f"Q{i}"), "answer": localized(f"A{i}")} for i in range(3)],
            "contact": {"heading": localized("Contact"), "text": localized("Get in touch")},
        }
    )


# What the user accepts on the checkout screen for the standard fake quote (12.00, one agreement).
ACCEPT = PurchaseRequest(agreement_types=["API_DPA"], price=12.0)


def make_client(handler) -> tuple[GddyClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(record))
    return GddyClient(BASE + "/", "secret-pat", 5, http=http), requests


def respond(body=None, status=200, headers=None):
    return lambda request: httpx.Response(status, json=body, headers=headers)


def prepare_site(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    orchestrator.choose_domain(run.id, "achaar1.com")
    orchestrator.generate_site(run.id, "achaar1.com", 12.0)
    return run


def quoted(orchestrator):
    """A run with its site generated and a quote taken, ready to buy."""
    run = prepare_site(orchestrator)
    orchestrator.quote_purchase(run.id)
    return run


# A real reply from `POST /registration-quotes` (token replaced), which matches the OpenAPI spec.
QUOTE = {
    "available": True,
    "domain": "achaar.com",
    "expiresAt": "2030-01-01T10:10:00Z",
    "inventory": "REGISTRY",
    "irreversible": True,
    "period": 1,
    "price": {"currencyCode": "USD", "value": 919},
    "quoteToken": "tok-1",
    "renewalPrice": {"currencyCode": "USD", "value": 1159},
    "requiredAgreements": [
        {
            "agreementType": "API_DPA",
            "title": "API Domain Purchase Agreement",
            "url": "https://www.godaddy.com/legal/agreements/api-domain-purchase-agreement",
        }
    ],
    "resolved": {"contactSource": "ACCOUNT", "registrantSummary": "A Founder (account identity)"},
}


def make_locked_quote(**changes) -> LockedQuote:
    base = dict(
        domain="achaar.com",
        period=1,
        price=9.19,
        currency="USD",
        token="tok-1",
        idempotency_key="key-1",
        agreements=[{"type": "API_DPA", "title": "T"}],
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    return LockedQuote(**{**base, **changes})
