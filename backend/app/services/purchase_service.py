import logging
import time
import uuid
from datetime import UTC, datetime

from app.clients.gddy_client import GddyClient
from app.core.config import Settings
from app.core.errors import ConfirmationMismatchError, PurchaseFailedError, QuoteExpiredError
from app.models import LockedQuote, Purchase
from app.schemas import PurchaseRequest

logger = logging.getLogger(__name__)


class PurchaseService:
    """Quotes and buys a domain.

    The quote is always real (it is free). In demo mode the registration is skipped: nothing is
    registered or charged, and the purchase is recorded as a demo. Outside demo mode,
    `GddyClient.register` is the only call that spends money.
    """

    def __init__(self, gddy: GddyClient, settings: Settings) -> None:
        self._gddy = gddy
        self._demo = settings.demo_mode
        self._poll_seconds = settings.purchase_poll_seconds
        self._poll_interval = settings.purchase_poll_interval_seconds

    def quote(self, domain: str) -> LockedQuote:
        quote = self._gddy.quote_registration(domain)
        # One key per quote: repeating the registration for this quote (after a timeout, say) is then
        # deduplicated by GoDaddy instead of buying the domain twice.
        return quote.model_copy(update={"demo": self._demo, "idempotency_key": str(uuid.uuid4())})

    @staticmethod
    def check_acceptance(quote: LockedQuote, accepted: PurchaseRequest) -> None:
        """Refuse unless the quote is still locked and the user accepted exactly what it says.

        Raises QuoteExpiredError, or ConfirmationMismatchError if the accepted agreements or price differ
        from the quote's, or if it has premium fees that were not acknowledged.
        """
        if quote.expires_at <= datetime.now(UTC):
            raise QuoteExpiredError()
        if (
            set(accepted.agreement_types) != {a.type for a in quote.agreements}
            or accepted.price != quote.price
            or (quote.fees and not accepted.acknowledged_fees)
        ):
            logger.warning("purchase confirmation does not match the quote domain=%s", quote.domain)
            raise ConfirmationMismatchError()

    def buy(self, quote: LockedQuote, agreed_at: datetime) -> Purchase:
        """Register the quoted domain, or pretend to in demo mode. Waits a while for GoDaddy to finish."""
        purchase = Purchase(
            domain=quote.domain,
            status="pending",
            demo=self._demo,
            price=quote.price,
            currency=quote.currency,
            agreed_at=agreed_at,
        )
        if self._demo:
            logger.warning("DEMO MODE: skipping POST /registrations domain=%s price=%s", quote.domain, quote.price)
            return purchase.model_copy(update={"status": "completed"})

        registration_id, status = self._gddy.register(quote, agreed_at)
        logger.warning("domain registration requested domain=%s registration_id=%s", quote.domain, registration_id)
        purchase = purchase.model_copy(update={"registration_id": registration_id})
        status, expires_at = self._poll(registration_id, status, self._poll_seconds)
        return self._with_outcome(purchase, status, expires_at)

    def refresh(self, purchase: Purchase) -> Purchase:
        """Check once on a purchase that was still pending. Never registers anything."""
        assert purchase.registration_id is not None  # only real purchases can be pending
        status, expires_at = self._gddy.get_registration(purchase.registration_id)
        return self._with_outcome(purchase, status, expires_at)

    def _poll(self, registration_id: str, status: str, wait_seconds: float) -> tuple[str, datetime | None]:
        """Poll until the registration is completed or failed, or until the wait runs out."""
        deadline = time.monotonic() + wait_seconds
        expires_at = None
        while status not in ("COMPLETED", "FAILED") and time.monotonic() < deadline:
            time.sleep(self._poll_interval)
            status, expires_at = self._gddy.get_registration(registration_id)
        return status, expires_at

    @staticmethod
    def _with_outcome(purchase: Purchase, status: str, expires_at: datetime | None) -> Purchase:
        if status == "FAILED":
            logger.error("registration failed domain=%s registration_id=%s", purchase.domain, purchase.registration_id)
            raise PurchaseFailedError()
        if status == "COMPLETED":
            return purchase.model_copy(update={"status": "completed", "expires_at": expires_at})
        return purchase.model_copy(update={"status": "pending"})
