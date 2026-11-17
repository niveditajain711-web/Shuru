import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import ClaudeError, DomainTakenError, GddyError
from app.main import create_app
from app.models import Brief, DomainOffer, Lang, SiteContent
from app.orchestrator import Orchestrator
from app.services.site_service import SiteService
from app.store import RunStore

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


class FakeClaude:
    def __init__(self) -> None:
        self.site_calls = 0
        self.fail = False

    def generate_brief(self, idea: str, lang: Lang) -> Brief:
        if self.fail:
            raise ClaudeError()
        return make_brief()

    def generate_site(self, brief: Brief, domain: str) -> SiteContent:
        self.site_calls += 1
        if self.fail:
            raise ClaudeError()
        return make_site()


class FakeDomains:
    def __init__(self) -> None:
        self.offers = [DomainOffer(name="achaar1.com", price=12.0, renewal_price=15.0, currency="USD")]
        self.fail = False
        self.taken = False
        self.fresh_price = 12.0
        self.last_names: list[str] = []

    def find_available(self, names: list[str]) -> list[DomainOffer]:
        self.last_names = names
        if self.fail:
            raise GddyError()
        return self.offers

    def confirm_available(self, domain: str) -> DomainOffer:
        if self.taken:
            raise DomainTakenError()
        return DomainOffer(name=domain, price=self.fresh_price, renewal_price=15.0, currency="USD")


@pytest.fixture
def claude() -> FakeClaude:
    return FakeClaude()


@pytest.fixture
def domains() -> FakeDomains:
    return FakeDomains()


@pytest.fixture
def orchestrator(tmp_path, claude, domains) -> Orchestrator:
    return Orchestrator(
        store=RunStore(tmp_path / "test.sqlite"),
        claude=claude,
        domains=domains,
        sites=SiteService(),
        settings=Settings(regeneration_cap=2),
    )


@pytest.fixture
def client(orchestrator) -> TestClient:
    return TestClient(create_app(orchestrator), raise_server_exceptions=False)
