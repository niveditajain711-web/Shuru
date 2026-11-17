import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.errors import DomainTakenError, GddyError
from app.models import DomainOffer
from app.services.gddy_client import GddyClient

logger = logging.getLogger(__name__)

_TLDS = ("com", "net", "io")
_SUGGEST_LIMIT = 5
_MAX_NAMES = 3  # how many name ideas are searched
_MAX_RESULTS = 10  # how many suggested domains are shown


class DomainService:
    """Finds domains to register, with their indicative prices.

    Suggestions are available by contract, so they are trusted as they are. The chosen domain is
    re-checked once (`confirm_available`), and the quote is the final authority.
    """

    def __init__(self, gddy: GddyClient) -> None:
        self._gddy = gddy

    def find_available(self, names: list[str]) -> list[DomainOffer]:
        """Suggest domains for the first few names and merge them, without duplicates.

        A failed search for one name is skipped so it does not hide the others.
        Raises GddyError only when every search failed.
        """
        results = self._in_parallel(lambda name: self._gddy.suggest(name, _TLDS, _SUGGEST_LIMIT), names[:_MAX_NAMES])
        unique: dict[str, DomainOffer] = {}
        for offers in results:
            for offer in offers:
                unique.setdefault(offer.name, offer)
        return list(unique.values())[:_MAX_RESULTS]

    def confirm_available(self, domain: str) -> DomainOffer:
        """Check the chosen domain against the registry. Returns it with its fresh price.

        Raises DomainTakenError if it can no longer be registered.
        """
        offer = self._gddy.check_availability(domain)
        if offer is None:
            raise DomainTakenError()
        return offer

    @staticmethod
    def _in_parallel[A, R](fn: Callable[[A], R], items: list[A]) -> list[R]:
        """Apply `fn` to every item concurrently, dropping items whose call raised GddyError."""
        if not items:
            return []
        with ThreadPoolExecutor(max_workers=len(items)) as pool:
            futures = [pool.submit(fn, item) for item in items]

        results: list[R] = []
        failures = 0
        for item, future in zip(items, futures):
            try:
                results.append(future.result())
            except GddyError:
                failures += 1
                logger.warning("gddy call failed, skipping item=%s", item)
        if failures == len(items):
            raise GddyError()
        return results
