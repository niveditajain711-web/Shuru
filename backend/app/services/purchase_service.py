import logging
import time
from datetime import datetime

from app.clients.gddy_client import GddyClient
from app.core.config import Settings
from app.core.errors import PurchaseFailedError
from app.models import Purchase, Quote

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

    def quote(self, domain: str) -> Quote:
        quote = self._gddy.quote_registration(domain)
        return quote.model_copy(update={"demo": self._demo})

    def buy(self, quote: Quote, agreed_at: datetime) -> Purchase:
        """Register the quoted domain, or pretend to in demo mode. Waits a while for GoDaddy to finish."""
        purchase = Purchase(
            domain=quote.domain,
            status="completed",
            demo=self._demo,
            price=quote.price,
            currency=quote.currency,
            agreed_at=agreed_at,
        )
        if self._demo:
            logger.warning("DEMO MODE: skipping POST /registrations domain=%s price=%s", quote.domain, quote.price)
            return purchase

        registration_id, status = self._gddy.register(quote, agreed_at)
        logger.warning("domain registration requested domain=%s registration_id=%s", quote.domain, registration_id)
        purchase.registration_id = registration_id
        return self._settle(purchase, status, None)

    def refresh(self, purchase: Purchase) -> Purchase:
        """Check on a purchase that was still pending. Never registers anything."""
        if purchase.demo or purchase.registration_id is None:
            return purchase.model_copy(update={"status": "completed"})
        status, expires_at = self._gddy.get_registration(purchase.registration_id)
        return self._settle(purchase.model_copy(), status, expires_at, wait=False)

    def _settle(self, purchase: Purchase, status: str, expires_at: datetime | None, wait: bool = True) -> Purchase:
        """Poll until the registration is completed or failed, or until the wait runs out."""
        deadline = time.monotonic() + (self._poll_seconds if wait else 0)
        while True:
            if status == "COMPLETED":
                purchase.status = "completed"
                purchase.expires_at = expires_at
                return purchase
            if status == "FAILED":
                logger.error("registration failed domain=%s registration_id=%s", purchase.domain, purchase.registration_id)
                raise PurchaseFailedError()
            if time.monotonic() >= deadline:
                purchase.status = "pending"
                return purchase
            time.sleep(self._poll_interval)
            status, expires_at = self._gddy.get_registration(purchase.registration_id or "")
