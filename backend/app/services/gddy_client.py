import logging
import re
import time
from collections.abc import Sequence
from decimal import Decimal

import httpx
from pydantic import BaseModel, ValidationError

from app.errors import GddyError
from app.models import DOMAIN_LABEL_PATTERN, DOMAIN_PATTERN, DomainOffer

logger = logging.getLogger(__name__)

_MAX_QUERY_LENGTH = 100  # the API's limit for `query`
_MAX_PAGE_SIZE = 50  # the API's limit for `pageSize`
_RETRY_AFTER_CAP_SECONDS = 3.0

# ISO-4217 minor units. Anything not listed has 2 decimals.
_ZERO_DECIMAL = {"BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
_THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}


class _Money(BaseModel):
    currencyCode: str
    value: int


class _TermPrice(BaseModel):
    term: str
    period: int
    price: _Money
    renewalPrice: _Money | None = None


class _Suggestion(BaseModel):
    domain: str
    prices: list[_TermPrice] = []


class _Suggestions(BaseModel):
    items: list[_Suggestion]


class _Availability(BaseModel):
    domain: str
    available: bool | None = None
    prices: list[_TermPrice] = []
    error: dict | None = None


class _Availabilities(BaseModel):
    items: list[_Availability]


class GddyClient:
    """The only module that calls the GoDaddy Domain Lifecycle API (v3).

    Authenticates with the PAT as a Bearer token. Every call has a timeout, a 429 is retried once,
    and every failure becomes `GddyError`; technical detail (status, `correlationId`, raw body)
    goes to the logs only, and the token is never logged.
    """

    def __init__(self, base_url: str, pat: str, timeout_seconds: float, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(timeout=timeout_seconds)
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {pat}", "Accept": "application/json"}

    def suggest(self, query: str, tlds: Sequence[str], limit: int) -> list[DomainOffer]:
        """Return suggested domains for a query. Suggestions are available by contract."""
        _require(len(query) <= _MAX_QUERY_LENGTH and re.fullmatch(DOMAIN_LABEL_PATTERN, query), "query")
        _require(0 < limit <= _MAX_PAGE_SIZE, "limit")
        body = self._send("GET", "/suggestions", params={"query": query, "tlds": ",".join(tlds), "pageSize": limit})
        parsed = _parse(_Suggestions, body, "suggestions")

        offers = []
        for item in parsed.items:
            offer = _to_offer(item.domain, item.prices)
            if offer is None:
                logger.warning("gddy suggestion without a usable 1-year price domain=%s", item.domain)
                continue
            offers.append(offer)
        return offers

    def check_availability(self, domain: str) -> DomainOffer | None:
        """Check one domain against the registry. Returns it with its price, or None if not available."""
        _require(re.fullmatch(DOMAIN_PATTERN, domain), "domain")
        body = self._send("POST", "/check-availability", json={"domains": [domain], "optimizeFor": "ACCURACY"})
        parsed = _parse(_Availabilities, body, "availability")
        if len(parsed.items) != 1:
            logger.error("gddy availability returned %d items for 1 domain", len(parsed.items))
            raise GddyError()

        result = parsed.items[0]
        if result.error is not None:
            logger.info("gddy domain could not be checked domain=%s error=%s", domain, result.error.get("name"))
            return None
        if not result.available:
            return None
        offer = _to_offer(result.domain, result.prices)
        if offer is None:
            logger.error("gddy available domain has no usable 1-year price domain=%s", domain)
            raise GddyError()
        return offer

    def _send(self, method: str, path: str, **kwargs: object) -> object:
        url = f"{self._base_url}{path}"
        started = time.monotonic()
        try:
            response = self._http.request(method, url, headers=self._headers, **kwargs)
            if response.status_code == 429:
                delay = _retry_delay(response)
                logger.warning("gddy rate limited path=%s, retrying in %.1fs", path, delay)
                time.sleep(delay)
                response = self._http.request(method, url, headers=self._headers, **kwargs)
        except httpx.HTTPError as exc:
            logger.error("gddy request failed method=%s path=%s error=%r", method, path, exc)
            raise GddyError() from exc

        logger.info(
            "gddy method=%s path=%s status=%d duration=%.2fs request_id=%s",
            method,
            path,
            response.status_code,
            time.monotonic() - started,
            response.headers.get("X-Request-Id"),
        )
        if response.status_code >= 400:
            logger.error(
                "gddy error method=%s path=%s status=%d request_id=%s body=%s",
                method,
                path,
                response.status_code,
                response.headers.get("X-Request-Id"),
                response.text[:500],
            )
            raise GddyError()
        try:
            return response.json()
        except ValueError as exc:
            logger.error("gddy returned invalid JSON path=%s status=%d body=%r", path, response.status_code, response.text[:200])
            raise GddyError() from exc


def _parse[M: BaseModel](model: type[M], body: object, what: str) -> M:
    try:
        return model.model_validate(body)
    except ValidationError as exc:
        logger.error("gddy unexpected %s output=%r error=%s", what, body, exc)
        raise GddyError() from exc


def _to_offer(domain: str, prices: list[_TermPrice]) -> DomainOffer | None:
    """Build an offer from the 1-year price. Returns None if there is none or the name is invalid."""
    one_year = next((p for p in prices if p.term == "YEAR" and p.period == 1), None)
    if one_year is None or not re.fullmatch(DOMAIN_PATTERN, domain):
        return None
    currency = one_year.price.currencyCode
    renewal = one_year.renewalPrice
    return DomainOffer(
        name=domain,
        price=_to_amount(one_year.price),
        renewal_price=_to_amount(renewal) if renewal and renewal.currencyCode == currency else None,
        currency=currency,
    )


def _to_amount(money: _Money) -> float:
    """Convert the API's integer minor units (`919` USD is 9.19) using the currency's decimals."""
    code = money.currencyCode.upper()
    decimals = 0 if code in _ZERO_DECIMAL else 3 if code in _THREE_DECIMAL else 2
    return float(Decimal(money.value).scaleb(-decimals))


def _retry_delay(response: httpx.Response) -> float:
    try:
        return min(max(float(response.headers.get("Retry-After", 1)), 0.0), _RETRY_AFTER_CAP_SECONDS)
    except ValueError:
        return 1.0


def _require(ok: object, what: str) -> None:
    """Reject values the API would not accept, before sending them."""
    if not ok:
        logger.error("gddy rejected invalid %s", what)
        raise GddyError()
