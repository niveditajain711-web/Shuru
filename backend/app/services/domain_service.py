import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.errors import GddyError
from app.models import DomainOffer
from app.services.gddy_client import GddyClient

logger = logging.getLogger(__name__)

_TLDS = ("com", "net", "io")
_SUGGEST_LIMIT = 5
_MAX_NAMES = 3  # how many name ideas are searched
_MAX_CANDIDATES = 10  # how many suggested domains are checked for availability


class DomainService:
    """Finds domains that are available to register, with their prices."""

    def __init__(self, gddy: GddyClient) -> None:
        self._gddy = gddy

    def find_available(self, names: list[str]) -> list[DomainOffer]:
        """Suggest domains for the first few names, then keep those that are available.

        Individual failed calls are skipped so one bad domain does not hide the others.
        Raises GddyError only when every call of a stage failed.
        """
        suggested = self._suggest(names[:_MAX_NAMES])
        candidates = list(dict.fromkeys(suggested))[:_MAX_CANDIDATES]

        results = self._in_parallel(self._gddy.check_availability, candidates)
        return [offer for offer in results if offer is not None]

    def _suggest(self, names: list[str]) -> list[str]:
        results = self._in_parallel(lambda name: self._gddy.suggest(name, _TLDS, _SUGGEST_LIMIT), names)
        return [domain for result in results for domain in result]

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
