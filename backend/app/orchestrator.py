import logging
import uuid
from datetime import UTC, datetime

from app.config import Settings
from app.errors import DomainNotAvailableError, InvalidRunStateError, RegenerationLimitError
from app.models import Lang, Run, RunState
from app.services.claude_service import ClaudeService
from app.services.domain_service import DomainService
from app.services.site_service import SiteService
from app.store import RunStore

logger = logging.getLogger(__name__)


class Orchestrator:
    """The fixed state machine that sequences the services. Code, not Claude, controls the flow.

    BRIEFED -> DOMAINS_LISTED -> DOMAIN_CHOSEN -> SITE_GENERATED

    Each step checks the run's state first, saves the new state before slow side effects where
    that lets the user retry, and never moves backwards. Nothing here can spend money.
    """

    def __init__(
        self,
        store: RunStore,
        claude: ClaudeService,
        domains: DomainService,
        sites: SiteService,
        settings: Settings,
    ) -> None:
        self._store = store
        self._claude = claude
        self._domains = domains
        self._sites = sites
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
        self._require_state(run, RunState.BRIEFED, RunState.DOMAINS_LISTED)

        run.domains = self._domains.find_available([keyword] if keyword else run.brief.name_ideas)
        run.state = RunState.DOMAINS_LISTED
        self._save(run)
        return run

    def choose_domain(self, run_id: str, domain: str) -> Run:
        """Step 3: record the chosen domain, then generate the site content for it.

        If generation fails, the run stays DOMAIN_CHOSEN and the same call can be retried.
        """
        run = self._store.get(run_id)
        self._require_state(run, RunState.DOMAINS_LISTED, RunState.DOMAIN_CHOSEN)

        chosen = next((offer for offer in run.domains if offer.name == domain), None)
        if chosen is None:
            logger.warning("domain not in listed offers run_id=%s domain=%s", run_id, domain)
            raise DomainNotAvailableError()

        run.domain = chosen
        run.state = RunState.DOMAIN_CHOSEN
        self._save(run)

        run.site = self._claude.generate_site(run.brief, chosen.name)
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
        self._require_state(run, RunState.SITE_GENERATED)
        return self._sites.render(run.site, run.domain.name, lang)

    def _save(self, run: Run) -> None:
        run.updated_at = datetime.now(UTC)
        self._store.save(run)

    @staticmethod
    def _require_state(run: Run, *allowed: RunState) -> None:
        if run.state not in allowed:
            logger.warning("invalid run state run_id=%s state=%s allowed=%s", run.id, run.state, allowed)
            raise InvalidRunStateError()
