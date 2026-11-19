from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ClaudeError, DomainTakenError, GddyError
from app.main import create_app
from app.models import Agreement, Brief, DomainOffer, Lang, LockedQuote, SiteContent
from app.repositories.run_store import RunStore
from app.services.orchestrator import Orchestrator
from app.services.purchase_service import PurchaseService
from app.services.site_service import SiteService
from app.utils.rate_limit import RateLimiter
from tests.helpers import make_brief, make_site


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


class FakePurchaseGddy:
    """Stands in for GddyClient on the purchase side. Records every call."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.quote_fail = False
        self.taken = False
        self.fees: list = []
        self.registration_status = "COMPLETED"
        self.statuses: list[str] = []  # what get_registration returns, in order
        self.expires_in = timedelta(minutes=10)

    def quote_registration(self, domain: str, period: int = 1) -> LockedQuote:
        self.calls.append("quote")
        if self.quote_fail:
            raise GddyError()
        if self.taken:
            raise DomainTakenError()
        return LockedQuote(
            domain=domain,
            period=period,
            price=12.0,
            renewal_price=15.0,
            currency="USD",
            fees=self.fees,
            agreements=[Agreement(type="API_DPA", title="Domain Purchase Agreement", url="https://example.test/a")],
            expires_at=datetime.now(UTC) + self.expires_in,
            token="secret-token",
        )

    def register(self, quote: LockedQuote, agreed_at: datetime) -> tuple[str, str]:
        self.calls.append("register")
        return "reg-1", self.registration_status

    def get_registration(self, registration_id: str) -> tuple[str, datetime | None]:
        self.calls.append("get_registration")
        status = self.statuses.pop(0) if self.statuses else "COMPLETED"
        return status, datetime.now(UTC) + timedelta(days=365)


@pytest.fixture
def gddy() -> FakePurchaseGddy:
    return FakePurchaseGddy()


@pytest.fixture
def demo_mode() -> bool:
    return True


@pytest.fixture
def claude() -> FakeClaude:
    return FakeClaude()


@pytest.fixture
def domains() -> FakeDomains:
    return FakeDomains()


@pytest.fixture
def orchestrator(tmp_path, claude, domains, gddy, demo_mode) -> Orchestrator:
    settings = Settings(
        regeneration_cap=2, demo_mode=demo_mode, purchase_poll_seconds=0, purchase_poll_interval_seconds=0
    )
    return Orchestrator(
        store=RunStore(tmp_path / "test.sqlite"),
        claude=claude,
        domains=domains,
        sites=SiteService(),
        purchases=PurchaseService(gddy, settings),
        regeneration_cap=2,
    )


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.error: Exception | None = None

    def send_contact(self, name: str, email: str, message: str) -> None:
        if self.error:
            raise self.error
        self.sent.append((name, email, message))


@pytest.fixture
def mailer() -> FakeMailer:
    return FakeMailer()


@pytest.fixture
def client(orchestrator, mailer) -> TestClient:
    return TestClient(
        create_app(orchestrator, mailer, RateLimiter(3, 3600), RateLimiter(5, 3600)), raise_server_exceptions=False
    )
