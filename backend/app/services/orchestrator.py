import logging
import uuid
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.errors import (
    ConfirmationMismatchError,
    DomainNotAvailableError,
    InvalidRunStateError,
    PurchaseFailedError,
    QuoteExpiredError,
    RegenerationLimitError,
)
from app.models import Lang, PurchaseRequest, Run, RunState
from app.services.claude_service import ClaudeService
from app.services.domain_service import DomainService
from app.services.purchase_service import PurchaseService
from app.services.site_service import SiteService
from app.repositories.run_store import RunStore

logger = logging.getLogger(__name__)


class Orchestrator:
    """The fixed state machine that sequences the services. Code, not Claude, controls the flow.

    BRIEFED -> DOMAINS_LISTED -> DOMAIN_CHOSEN -> SITE_GENERATED -> (PURCHASING ->) PURCHASED

    Each step checks the run's state first and saves the new state before slow side effects where
    that lets the user retry. The user may change their mind about the domain (DOMAIN_CHOSEN back
    to DOMAINS_LISTED), but once the site is generated nothing moves backwards.
    Only `purchase` can spend money, and not in demo mode (see `PurchaseService`).
    """

    def __init__(
        self,
        store: RunStore,
        claude: ClaudeService,
        domains: DomainService,
        sites: SiteService,
        purchases: PurchaseService,
        settings: Settings,
    ) -> None:
        self._store = store
        self._claude = claude
        self._domains = domains
        self._sites = sites
        self._purchases = purchases
        self._regeneration_cap = settings.regeneration_cap

    def create_run(self, idea: str, lang: Lang) -> Run:
        """Step 1: turn the idea into a brief. The run only exists once the brief is valid."""
        brief = self._claude.generate_brief(idea, lang)
        now = datetime.now(UTC)
        run = Run(
            id=uuid.uuid4().hex,
            state=RunState.BRIEFED,
            lang=lang,
            idea=idea,
            brief=brief,
            created_at=now,
            updated_at=now,
        )
        self._save(run)
        return run

    def get_run(self, run_id: str) -> Run:
        return self._store.get(run_id)

    def list_domains(self, run_id: str, keyword: str | None = None) -> Run:
        """Step 2: find available domains for the brief's names, or for the user's own keyword."""
        run = self._store.get(run_id)
        self._require_state(run, RunState.BRIEFED, RunState.DOMAINS_LISTED, RunState.DOMAIN_CHOSEN)

        run.domains = self._domains.find_available([keyword] if keyword else run.brief.name_ideas)
        run.domain = None
        run.state = RunState.DOMAINS_LISTED
        self._save(run)
        return run

    def choose_domain(self, run_id: str, domain: str) -> Run:
        """Step 3: record the chosen domain with its fresh price. No Claude call yet.

        The domain is re-checked against the registry once. The user then reviews the cost and
        confirms with `generate_site`, so Claude only runs for a domain they are happy to buy.
        """
        run = self._store.get(run_id)
        self._require_state(run, RunState.DOMAINS_LISTED, RunState.DOMAIN_CHOSEN)

        chosen = next((offer for offer in run.domains if offer.name == domain), None)
        if chosen is None:
            logger.warning("domain not in listed offers run_id=%s domain=%s", run_id, domain)
            raise DomainNotAvailableError()

        run.domain = self._domains.confirm_available(chosen.name)
        run.state = RunState.DOMAIN_CHOSEN
        self._save(run)
        return run

    def generate_site(self, run_id: str, domain: str, price: float) -> Run:
        """Step 4: the user confirmed the cost, so generate the site content.

        `domain` and `price` are what the user saw; they must match the stored choice. If generation
        fails, the run stays DOMAIN_CHOSEN and the same call can be retried.
        """
        run = self._store.get(run_id)
        self._require_state(run, RunState.DOMAIN_CHOSEN)
        if run.domain is None or run.domain.name != domain or run.domain.price != price:
            logger.warning("confirmation does not match run_id=%s domain=%s price=%s", run_id, domain, price)
            raise ConfirmationMismatchError()

        run.site = self._claude.generate_site(run.brief, run.domain.name)
        run.state = RunState.SITE_GENERATED
        self._save(run)
        return run

    def regenerate_site(self, run_id: str) -> Run:
        """Generate the site content again, up to the regeneration cap."""
        run = self._store.get(run_id)
        self._require_state(run, RunState.SITE_GENERATED)
        if run.regenerations >= self._regeneration_cap:
            raise RegenerationLimitError(self._regeneration_cap)

        run.site = self._claude.generate_site(run.brief, run.domain.name)
        run.regenerations += 1
        self._save(run)
        return run

    def render_preview(self, run_id: str, lang: Lang) -> str:
        run = self._store.get(run_id)
        self._require_state(run, RunState.SITE_GENERATED, RunState.PURCHASING, RunState.PURCHASED)
        return self._sites.render(run.site, run.domain.name, lang)

    def quote_purchase(self, run_id: str) -> Run:
        """Step 5a: lock the price of the chosen domain. Free. Replaces any earlier quote."""
        run = self._store.get(run_id)
        self._require_state(run, RunState.SITE_GENERATED)
        assert run.domain is not None  # a generated site always has a chosen domain

        run.quote = self._purchases.quote(run.domain.name)
        self._save(run)
        return run

    def purchase(self, run_id: str, request: PurchaseRequest) -> Run:
        """Step 5b: the user accepted the agreements and the quoted price, so buy the domain.

        What they accepted must match the stored quote exactly, and the quote must still be locked.
        If GoDaddy has not finished yet the run becomes PURCHASING; `refresh_purchase` then checks on it.
        """
        run = self._store.get(run_id)
        self._require_state(run, RunState.SITE_GENERATED)

        quote = run.quote
        if quote is None:
            logger.warning("purchase without a quote run_id=%s", run_id)
            raise InvalidRunStateError()
        if quote.expires_at <= datetime.now(UTC):
            raise QuoteExpiredError()
        if (
            set(request.agreement_types) != {a.type for a in quote.agreements}
            or request.price != quote.price
            or (quote.fees and not request.acknowledged_fees)
        ):
            logger.warning("purchase confirmation does not match the quote run_id=%s", run_id)
            raise ConfirmationMismatchError()

        try:
            # The user clicked accept to send this request, so now is the time of consent.
            run.purchase = self._purchases.buy(quote, datetime.now(UTC))
        except PurchaseFailedError:
            run.quote = None  # the token is spent, so the next attempt needs a new quote
            self._save(run)
            raise
        return self._finish_purchase(run)

    def refresh_purchase(self, run_id: str) -> Run:
        """Check on a purchase GoDaddy had not finished. Never registers anything."""
        run = self._store.get(run_id)
        self._require_state(run, RunState.PURCHASING)
        assert run.purchase is not None

        run.purchase = self._purchases.refresh(run.purchase)
        return self._finish_purchase(run)

    def _finish_purchase(self, run: Run) -> Run:
        assert run.purchase is not None
        run.state = RunState.PURCHASED if run.purchase.status == "completed" else RunState.PURCHASING
        self._save(run)
        return run

    def _save(self, run: Run) -> None:
        run.updated_at = datetime.now(UTC)
        self._store.save(run)

    @staticmethod
    def _require_state(run: Run, *allowed: RunState) -> None:
        if run.state not in allowed:
            logger.warning("invalid run state run_id=%s state=%s allowed=%s", run.id, run.state, allowed)
            raise InvalidRunStateError()
